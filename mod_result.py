from .setup import *
from .storage import CandidateStore, DecisionStore, GroupStore, RunStore, get_db_path, init_db
import json


class ModuleResult(PluginModuleBase):

    def __init__(self, P):
        super(ModuleResult, self).__init__(P, name='result', first_menu='setting')
        self.db_default = {
            f'{self.name}_db_version': '1',
            'result_last_run_summary': 'No runs yet.',
        }


    def process_command(self, command, arg1, arg2, arg3, req):
        db_path = get_db_path(P.ModelSetting.get('base_storage_db_path'))
        init_db(db_path)
        if command == 'summary':
            runs = RunStore.list_recent(db_path=db_path)
            return jsonify({'ret': 'success', 'summary': {'mode': P.ModelSetting.get('task_run_mode'), 'note': P.ModelSetting.get('result_last_run_summary'), 'latest_run': runs[0] if runs else None}})
        elif command == 'runs':
            runs = RunStore.list_recent(db_path=db_path)
            enriched = []
            for item in runs:
                summary = {}
                try:
                    summary = json.loads(item.get('summary_json') or '{}')
                except Exception:
                    summary = {'raw_summary': item.get('summary_json')}
                item['summary'] = summary
                enriched.append(item)
            return jsonify({'ret': 'success', 'list': enriched})
        elif command == 'groups':
            run_id = req.form.get('run_id') or arg1
            only_duplicates = (req.form.get('only_duplicates') or 'true').lower() == 'true'
            items = GroupStore.list_by_run(int(run_id), db_path=db_path) if run_id else []
            if only_duplicates:
                items = [item for item in items if item.get('candidate_count', 0) > 1]
            return jsonify({'ret': 'success', 'list': items, 'only_duplicates': only_duplicates})
        elif command == 'group_detail':
            group_id = req.form.get('group_id') or arg1
            if group_id:
                return jsonify({'ret': 'success', 'group': GroupStore.get(int(group_id), db_path=db_path), 'candidates': CandidateStore.list_by_group(int(group_id), db_path=db_path), 'decisions': DecisionStore.list_by_group(int(group_id), db_path=db_path)})
            return jsonify({'ret': 'success', 'group': None, 'candidates': [], 'decisions': []})
        elif command == 'decision':
            group_id = int(req.form.get('group_id') or arg1)
            run_id = int(req.form.get('run_id') or arg2)
            action = req.form.get('action') or 'reviewed'
            note = req.form.get('note') or ''
            DecisionStore.create(run_id, group_id, action, note=note, payload={}, db_path=db_path)
            GroupStore.update_review_status(group_id, action, rationale=note, db_path=db_path)
            candidates = CandidateStore.list_by_group(group_id, db_path=db_path)
            for candidate in candidates:
                if candidate.get('is_winner'):
                    CandidateStore.update_action(candidate['id'], 'keep', action_reason='winner preserved by review', action_status=action, db_path=db_path)
                else:
                    if action == 'approved':
                        planned_action = candidate.get('planned_action') or 'hold'
                        action_reason = candidate.get('action_reason') or 'approved from review queue'
                    elif action == 'rejected':
                        planned_action = 'keep'
                        action_reason = 'rejected from review queue'
                    else:
                        planned_action = candidate.get('planned_action') or 'review'
                        action_reason = 'held for later review'
                    CandidateStore.update_action(candidate['id'], planned_action, action_reason=action_reason, action_status=action, db_path=db_path)
            return jsonify({'ret': 'success', 'msg': '리뷰 상태를 저장했습니다.'})
        return jsonify({'ret': 'success'})

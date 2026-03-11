import re


KNOWN_SOURCE_TAGS = ['NF', 'AMZN', 'DSNP', 'WEB-DL', 'WEBRip', 'HDTV', 'BluRay']
KNOWN_CODECS = ['H265', 'HEVC', 'H264', 'X264', 'X265']
KNOWN_RESOLUTIONS = ['2160p', '1080p', '720p', '480p']


def normalize_title(text):
    if not text:
        return ''
    return re.sub(r'[^A-Za-z0-9가-힣]+', '', text).lower()


def extract_release_group(filename):
    base = filename.rsplit('.', 1)[0]
    match = re.search(r'-([A-Za-z0-9]+)$', base)
    if match:
        return match.group(1).upper()
    return ''


def extract_resolution(filename):
    for token in KNOWN_RESOLUTIONS:
        if token.lower() in filename.lower():
            return token
    return ''


def extract_codec(filename):
    upper = filename.upper()
    for token in KNOWN_CODECS:
        if token in upper:
            return token
    return ''


def extract_source_tags(filename):
    found = []
    upper = filename.upper()
    for token in KNOWN_SOURCE_TAGS:
        if token.upper() in upper:
            found.append(token.upper())
    return found


def extract_episode_token(filename):
    base = filename.rsplit('.', 1)[0]
    for pattern in [r'(S\d{1,2}E\d{1,3})', r'(E\d{1,4})', r'(\d{6})']:
        match = re.search(pattern, base, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return ''


def extract_title_part(filename):
    base = filename.rsplit('.', 1)[0]
    token = extract_episode_token(base)
    if token:
        idx = base.upper().find(token)
        if idx > 0:
            return base[:idx].strip(' .-_')
    return base.strip(' .-_')


def build_group_key(filename):
    title = normalize_title(extract_title_part(filename))
    token = extract_episode_token(filename)
    if not title:
        title = normalize_title(filename)
    if token:
        return f'{title}|{token.lower()}'
    return title


def parse_priority_list(raw_value):
    if not raw_value:
        return []
    return [x.strip().upper() for x in re.split(r'[|,\n]+', raw_value) if x.strip()]


def score_filename(filename, preferred_release='', preferred_source='', preferred_resolution=''):
    release = extract_release_group(filename)
    resolution = extract_resolution(filename)
    codec = extract_codec(filename)
    sources = extract_source_tags(filename)

    release_priority = parse_priority_list(preferred_release)
    source_priority = parse_priority_list(preferred_source)
    resolution_priority = parse_priority_list(preferred_resolution)

    score = 0
    if release and release in release_priority:
        score += (len(release_priority) - release_priority.index(release)) * 100
    if resolution and resolution.upper() in [x.upper() for x in resolution_priority]:
        normalized = [x.upper() for x in resolution_priority]
        score += (len(normalized) - normalized.index(resolution.upper())) * 20
    for source in sources:
        if source in source_priority:
            score += (len(source_priority) - source_priority.index(source)) * 15
            break
    if codec in ['H265', 'HEVC', 'X265']:
        score += 10
    elif codec:
        score += 5

    return {
        'filename': filename,
        'group_key': build_group_key(filename),
        'title': extract_title_part(filename),
        'episode_token': extract_episode_token(filename),
        'release_group': release,
        'sources': sources,
        'resolution': resolution,
        'codec': codec,
        'score': score,
    }

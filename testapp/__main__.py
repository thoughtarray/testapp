import argparse
import json
import logging
import re
from urlparse import urlparse

import flask
import requests

NAME = 'testapp'

logger = logging.getLogger(NAME)
app = flask.Flask(NAME)

@app.route('/')
def index():
    mode = app.config['S']['mode']

    if mode == 'stand-alone':
        return _stand_alone(app.config['S'], flask.request)

    if mode == 'static-dependency':
        return _static_dependency(app.config['S'], flask.request)

    if mode == 'dynamic-dependency':
        return _dynamic_dependency(app.config['S'], flask.request)

def _stand_alone(settings, request):
    http_code, http_body = settings['return']

    # stand-alone mode may recieve chain-script requests (most likely the end)
    is_chain_request = 'chain' in request.args

    if is_chain_request:
        return json.dumps(http_body), http_code, None

    return http_body, http_code, None

def _static_dependency(settings, request):
    is_single_dep = len(settings['static_deps']) == 1
    is_chain_request = 'chain' in request.args
    chain = []

    # Shorten chain by one link if possible
    if is_chain_request:
        raw_chain = request.args.get('chain', None)
        chain = raw_chain.split(',') if raw_chain else []
        if len(chain) and chain[0] == settings['name']: chain = chain[1:]

    http_code, http_body = settings['return']

    # Same action for single or multi deps with chain-script request
    if is_chain_request:
        # If chain is done, return
        if not len(chain):
            return json.dumps([http_body]), http_code, None

        next_dep = chain[0]
        # Chain link must exist in dependencies
        if next_dep not in settings['static_deps']:
            return json.dumps('{} does not have dependency {}' \
                .format(settings['name'], next_dep)), 404, None

        url = normalize_url(settings['static_deps'][next_dep])
        query_params = { 'chain': ','.join(chain) }

        try:
            r = requests.get(url, params=query_params, headers=settings['headers'])
        except requests.ConnectionError as e:
            loc = urlparse(url).netloc
            body = "Error contacting {}".format(loc)
            return json.dumps(body), 404, None

        try:
            r_content = json.loads(r.content)
        except ValueError:
            # Content isn't JSON; must be a plain string; turn into arr
            r_content = [r.content]

        # Combine last instance's return with this instance's return
        r_content = [http_body] + r_content if isinstance(r_content, list) \
            else [http_body, r_content]

        return json.dumps(r_content), http_code, None

    # Single dep doesn't require chain-script request
    if is_single_dep:
        url = normalize_url(settings['static_deps'].items()[0][1])
        r = requests.get(url, headers=settings['headers'])
        return r.content, r.status_code, None

    # Multi dep requires chain-script request
    return '{} has multiple dependencies; chain-script request required' \
        .format(settings['name']), 400, None

def _dynamic_dependency(settings, request):
    is_chain_request = 'chain' in request.args
    chain = []

    # Shorten chain by one link if possible
    if is_chain_request:
        raw_chain = request.args.get('chain', None)
        chain = raw_chain.split(',') if raw_chain else []
        if len(chain) and chain[0] == settings['name']: chain = chain[1:]

    http_code, http_body = settings['return']

    # Same action for single or multi deps with chain-script request
    if is_chain_request:
        # If chain is done, return
        if not len(chain):
            return json.dumps([http_body]), http_code, None

        next_dep = chain[0]

        # Substitute symbol for dependency
        url = settings['dynamic_dep'].format(next_dep)
        url = normalize_url(url)
        headers = s['headers'].copy()
        for h_k, h_v in headers.items():
            if '{}' in h_v:
                headers[h_k] = h_v.format(next_dep)

        query_params = { 'chain': ','.join(chain) }

        try:
            print headers
            r = requests.get(url, params=query_params, headers=headers)
        except requests.ConnectionError as e:
            loc = urlparse(url).netloc
            body = "Error contacting {}".format(loc)
            return json.dumps(body), 404, None

        try:
            r_content = json.loads(r.content)
        except ValueError:
            # Content isn't JSON; must be a plain string; turn into arr
            r_content = [r.content]

        # Combine last instance's return with this instance's return
        r_content = [http_body] + r_content if isinstance(r_content, list) \
            else [http_body, r_content]

        return json.dumps(r_content), http_code, None

    # If non-chain request
    return http_body, http_code, None


@app.route('/meta/health')
def health():
    return '[]'

# ---

def normalize_url(url):
    url = url.strip()
    match = re.match(r'^(http:\/\/|https:\/\/)', url)

    if not match:
        return 'http://{}'.format(url)

    return url

def _kv_to_tup(s):
    match = re.match(r'(.*)=(.*)', s)
    if not match:
        raise ValueError(s)

    return match.group(1).strip(), match.group(2).strip()

def _kv_arr_to_dict(a):
    return dict([ _kv_to_tup(i) for i in a ])

if __name__ == '__main__':
    global app_name

    # Prep logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - '
        '%(levelname)s - %(message)s')

    # Prep args
    parser = argparse.ArgumentParser(NAME)

    parser.add_argument('-n', '--name', default=NAME,
        help='Name of instance; default: testapp')
    parser.add_argument('--host', default='127.0.0.1', metavar='IP',
        help='Host to accept requests; default: 127.0.0.1')
    parser.add_argument('-p', '--port', default=80,
        help='Port of instance; default: 80')
    parser.add_argument('-r', '--return', metavar='CODE:MESSAGE',
        help='Success return; default: 200:NameOfInstance')
    parser.add_argument('-s', '--static', action='append', default=[],
        dest='static_deps', metavar='NAME=URL',
        help='Starts static-dependency mode (additive property)')
    parser.add_argument('-d', '--dynamic', metavar='URL', dest='dynamic_dep',
        help='Starts dynamic-dependency mode; URL may contain "{}"')
    parser.add_argument('-H', '--header', action='append', default=[],
        dest='headers', metavar='KEY=VALUE',
        help='HTTP header (additive property); VALUE may use "{}" in ' \
            'dynamic-dependency mode')

    s = vars(parser.parse_args())

    # Computed defaults
    s['return'] = s['return'] or "200:{}".format(s['name'])

    # Validate args

    s['mode'] = 'stand-alone'

    # port
    try:
        s['port'] = int(s['port'])
        if not 1 <= s['port'] <= 65535:
            raise ValueError()
    except ValueError:
        print 'Port must be an integer between 1-65535'
        exit(3)

    # return
    match = re.match(r'(\d{3}):(.*)', s['return'])
    if not match:
        print 'Return must be formatted as CODE:MESSAGE where CODE is a ' \
            '3-digit http status code and MESSAGE is any arbitrary string'
        exit(3)

    http_code, http_body = match.group(1).strip(), match.group(2).strip()
    s['return'] = http_code, http_body

    # static
    try:
        s['static_deps'] = _kv_arr_to_dict(s['static_deps'])
    except ValueError as e:
        print 'Static (dependency) "{}" must be formatted as KEY=VALUE where ' \
        'KEY and VALUE are any arbitrary strings'.format(e.value)
        exit(3)

    try:
        s['headers'] = _kv_arr_to_dict(s['headers'])
    except ValueError as e:
        print 'Header "{}" must be formatted as KEY=VALUE where KEY and ' \
            'VALUE are any arbitrary strings'.format(e.value)
        exit(3)

    if len(s['static_deps']):
        s['mode'] = 'static-dependency'

    # dynamic
    if s['dynamic_dep'] and len(s['static_deps']):
        print 'Cannot be ran in static-dependency and dynamic-dependency mode'
        exit(3)

    s['mode'] = 'dynamic-dependency'

    has_sub_symbol = False
    if '{}' in s['dynamic_dep']: has_sub_symbol = True
    for h in s['headers'].values():
        if '{}' in h: has_sub_symbol = True

    if not has_sub_symbol:
        print 'URL or a header must have substitue symbol "{}" when in ' \
            'dynamic-dependency mode'
        exit(3)

    # Run app
    app.config['S'] = s
    app.run(host=s['host'], port=s['port'])

import argparse
import logging
import re

import flask
import requests

NAME = 'testapp'

logger = logging.getLogger(NAME)
app = flask.Flask(NAME)

@app.route('/')
def index():
    http_code, http_body = app.config['S']['return']
    return http_body, http_code, None

@app.route('/meta/health')
def health():
    return '[]'

if __name__ == '__main__':
    global app_name

    # Prep logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - '
        '%(levelname)s - %(message)s')

    # Prep args
    parser = argparse.ArgumentParser(NAME)

    parser.add_argument('-n', '--name', default=NAME,
        help='Name of instance; default: testapp')
    parser.add_argument('-p', '--port', default=80,
        help='Port of instance; default: 80')
    parser.add_argument('-r', '--return', default='200:' + NAME,
        metavar='CODE:MESSAGE',
        help='Success return; default: 200:NameOfInstance')
    parser.add_argument('-H', '--header', action='append', default=[],
        dest='headers', help='HTTP header (additive property); may use '
            '"{}" in dynamic-dependency mode')

    s = vars(parser.parse_args())

    # Validate args
    try:
        s['port'] = int(s['port'])
        if not 1 <= s['port'] <= 65535:
            raise ValueError()
    except ValueError:
        print 'Port must be an integer between 1-65535'
        exit(3)

    match = re.match(r'(\d{3}):(.*)', s['return'])
    if not match:
        print 'Return must be formatted as CODE:MESSAGE where CODE is a ' \
            '3-digit http status code and MESSAGE is any arbitrary string'
        exit(3)

    http_code, http_body = match.group(1).strip(), match.group(2).strip()
    s['return'] = http_code, http_body

    headers = []
    for h in s['headers']:
        match = re.match(r'(.*)=(.*)', h)
        if not match:
            print 'Header "{}" must be formatted as KEY=VALUE where KEY and ' \
                'VALUE are any arbitrary strings'.format(h)
            exit(3)
        h = match.group(1).strip(), match.group(2).strip()
        headers.append(h)
    s['headers'] = headers

    # Run app
    app.config['S'] = s
    app.run(port=s['port'])

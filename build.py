#!/usr/bin/python

import re
import os
import sys
from navio.builder import task, nsh, sh


@task()
def apidoc():
    """
    Generate API documentation using epydoc.
    """
    nsh.epydoc('--config', 'epydoc.config')


@task()
def validate():
    # if os.environ.get('TRAVIS', 'false') == 'false':
    #     nsh.travis('lint')
    nsh.pycodestyle('build.py', 'setup.py', '--max-line-length=180')
    nsh.pycodestyle('navio/', '--max-line-length=180')


@task(validate)
def build():
    nsh.python('setup.py', 'sdist', 'bdist_wheel', '--universal')


@task(build)
def test(*args):
    """
    Run unit tests.
    """
    nsh.python('setup.py', 'test')


@task()
def check_uncommited():
    result = sh.git('status', '--porcelain', '--untracked-files=no')
    if result:
        print('There are uncommited files:\n{}'.format(result))
        raise Exception('There are uncommited files:\n{}'.format(result))


@task()
def update_version(ver=None):
    with open('navio/meta_aws.py', 'r') as f:
        file_str = f.read()

    if not ver:
        regexp = re.compile(r'__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*')
        m = regexp.search(file_str)
        if m:
            ver = m.group(1)

    minor_ver = int(ver[ver.rfind('.') + 1:])
    ver = '{}.{}'.format(ver[:ver.rfind('.')], minor_ver + 1)

    file_str = re.sub(
        r'__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*',
        r'__version__ = "{}"\n'.format(ver),
        file_str)

    with open('navio/meta_aws.py', 'w') as f:
        f.write(file_str)

    nsh.git('commit', 'navio/meta_aws.py', '-m', 'Version updated to {}'.format(ver))


@task()
def create_tag():
    with open('navio/meta_aws.py', 'r') as f:
        file_str = f.read()
    regexp = re.compile(r'__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*')
    m = regexp.search(file_str)
    if m:
        ver = m.group(1)
    else:
        raise "Can't find/parse current version in './navio/meta_aws.py'"

    nsh.git('tag', '-a', '-m', 'Tagging version {}'.format(ver), ver)


@task()
def push():
    nsh.git('push', '--verbose')
    nsh.git('push', '--tags', '--verbose')


@task(validate)
def release(ver=None):
    check_uncommited()
    update_version(ver)
    create_tag()
    push()


@task(test)
def pypi():
    args = ['upload']

    travis_pull_request = os.environ.get('TRAVIS_PULL_REQUEST', False) == 'true'
    travis_tag = os.environ.get('TRAVIS_TAG', False)

    if not travis_pull_request and travis_tag:
        args.append('--repository-url')
        args.append('https://upload.pypi.org/legacy/')
    else:
        args.append('--skip-existing')
        args.append('--repository-url')
        args.append('https://test.pypi.org/legacy/')

    args.append('dist/navio-aws-*')
    nsh.twine(args)


__DEFAULT__ = test

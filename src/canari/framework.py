from subprocess import Popen
import os
import re

from canari.mode import is_remote_exec_mode
from canari.resource import external_resource
from canari.utils.stack import calling_package

__author__ = 'Nadeem Douba'
__copyright__ = 'Copyright 2015, Canari Project'
__credits__ = []

__license__ = 'GPLv3'
__version__ = '0.1'
__maintainer__ = 'Nadeem Douba'
__email__ = 'ndouba@gmail.com'
__status__ = 'Development'

__all__ = [
    'RequireSuperUser',
    'Deprecated',
    'EnableRemoteExecution',
    'EnableDebugWindow',
    'ExternalCommand'
]


def RequireSuperUser(transform):
    """
    Marks the transform as a privileged transform which requires root access to execute. Upon transform execution, a
    sudo login box will appear prompting the user to enter their sudo password in the event that there isn't a pre-
    existing sudo session.

    .. note::
    This is not compatible with Windows. UAC must be turned off for privileged functions to execute.

    :param transform: the transform class that will be marked as privileged.
    :return: the superuser'ed transform class.

    :Example:

    @RequireSuperUser
    class MyTransform(Transform):
        pass
    """
    transform.superuser = True
    return transform


def Deprecated(transform):
    """
    Marks the transform as deprecated.

    :Example:

    @Deprecated
    class MyTransform(Transform):
        pass

    :param transform: the transform class that will be marked as deprecated.
    :return: the deprecated transform class.
    """
    transform.deprecated = True
    return transform


def EnableRemoteExecution(transform):
    """
    Marks the transform as a remote transform. This allows Plume to import and execute the transform.

    :Example:

    @EnableRemoteExecution
    class MyTransform(Transform):
        pass

    :param transform: the transform class that will be marked as deprecated.
    :return: the deprecated transform class.
    """
    transform.remote = True
    return transform


class RequestFilter(object):

    def __init__(self, filter_, remote_only=False, **kwargs):
        self.filter = filter_
        self.remote_only = remote_only

    def __call__(self, transform):
        if callable(filter):
            if self.remote_only and is_remote_exec_mode():
                orig_do_transform = transform.do_transform

                def do_transform(self_, request, response, config):
                    if self.filter.__call__(request, response, config):
                        return response
                    return orig_do_transform(self_, request, response, config)

                transform.do_transform = do_transform
            return transform
        raise ValueError('Expected callable (got %s instead).' % type(self.filter).__name__)


def EnableDebugWindow(transform):
    """
    TODO.

    :Example:

    @EnableDebugWindow
    MyTransform(Transform):
        pass

    :param transform: the transform class that will be marked as deprecated.
    :return: the deprecated transform class.
    """
    transform.debug = True
    return transform


class ExternalCommand(object):
    def __init__(self, interpreter, program, args=None):
        if args is None:
            args = []
        self.args = []

        if interpreter:
            self.args.append(interpreter)
            libpath = external_resource(
                os.path.dirname(program),
                '%s.resources.external' % calling_package()
            )
            if interpreter.startswith('perl') or interpreter.startswith('ruby'):
                self.args.append('-I%s' % libpath)
            elif interpreter.startswith('java'):
                self.args.extend(['-cp', libpath])

        if ' ' in program:
            raise ValueError('Transform name %r cannot have spaces.' % program)
        else:
            self.args.append(
                external_resource(
                    program,
                    '%s.resources.external' % calling_package()
                )
            )

        if isinstance(args, basestring):
            self.args = re.split(r'\s+', args)
        else:
            self.args.extend(args)

    def __call__(self, request, *args):
        self.args.append(request.entity.value)
        if isinstance(request.parameters, list) and request.parameters:
            self.args.extend(request.parameters)
        if request.entity.fields:
            self.args.append(
                '#'.join(
                    ['%s=%s' % (k, v.value.replace('#', '\\#').replace('=', '\\='))
                     for k, v in request.entity.fields.iteritems()]
                )
            )
        p = Popen(self.args)
        p.communicate()
        exit(p.returncode)

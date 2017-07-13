# Copyright (c) 2016, Daniele Venzano
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions needed by the Zoe REST API."""

import base64
import logging
import functools
from typing import Tuple

import tornado.web

from zoe_lib.config import get_conf

from zoe_api.exceptions import ZoeRestAPIException, ZoeNotFoundException, ZoeAuthException, ZoeException
from zoe_api.auth.base import BaseAuthenticator  # pylint-bug #1063 pylint: disable=unused-import
from zoe_api.auth.ldap import LDAPAuthenticator
from zoe_api.auth.file import PlainTextAuthenticator
from zoe_api.auth.ldapsasl import LDAPSASLAuthenticator

log = logging.getLogger(__name__)


def catch_exceptions(func):
    """
    Decorator function used to work around the static exception system available in Flask-RESTful
    :param func:
    :return:
    """
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        """The actual decorator."""
        self = args[0]
        try:
            return func(*args, **kwargs)
        except ZoeRestAPIException as e:
            if e.status_code != 401:
                log.exception(e.message)
            self.set_status(e.status_code)
            self.write({'message': e.message})
        except ZoeNotFoundException as e:
            self.set_status(404)
            self.write({'message': e.message})
        except ZoeAuthException as e:
            self.set_status(401)
            self.add_header('WWW-Authenticate', 'Basic realm="Login Required"')
            self.write({'message': e.message})
        except ZoeException as e:
            self.set_status(400)
            self.write({'message': e.message})
        except Exception as e:
            self.set_status(500)
            log.exception(str(e))
            self.write({'message': str(e)})

    return func_wrapper


def needs_auth(func):
    """Decorator function used to check for authentication. Mimics the Tornado @authenticated decorator,
    but does not redirect, since this is a REST API."""
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        """The actual decorator."""
        self = args[0]
        if not self.current_user:
            self.set_status(401)
            self.add_header('WWW-Authenticate', 'Basic realm="Login Required"')
            return
        return func(*args, **kwargs)

    return func_wrapper


def try_basic_auth(handler: tornado.web.RequestHandler) -> Tuple[str, str]:
    """Try to authenticate a request with HTTP basic auth."""
    auth_header = handler.request.headers.get('Authorization')
    if auth_header is None or not auth_header.startswith('Basic '):
        raise ZoeAuthException()

    auth_decoded = base64.decodebytes(bytes(auth_header[6:], 'ascii')).decode('utf-8')
    username, password = auth_decoded.split(':', 2)

    if get_conf().auth_type == 'text':
        authenticator = PlainTextAuthenticator()  # type: BaseAuthenticator
    elif get_conf().auth_type == 'ldap':
        authenticator = LDAPAuthenticator()  # type: BaseAuthenticator
    elif get_conf().auth_type == 'ldapsasl':
        authenticator = LDAPSASLAuthenticator()  # type: BaseAuthenticator
    else:
        log.error('Configuration error, unknown authentication method: {}'.format(get_conf().auth_type))
        raise ZoeAuthException()

    uid, role = authenticator.auth(username, password)
    if uid is None:
        raise ZoeAuthException()
    return uid, role

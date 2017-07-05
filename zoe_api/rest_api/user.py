# Copyright (c) 2017, Daniele Venzano, Quang-Nhat Hoang-Xuan
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

"""The User API endpoint."""

from tornado.web import RequestHandler
import tornado.escape

from zoe_api.rest_api.utils import get_auth, catch_exceptions, manage_cors_headers
from zoe_api.api_endpoint import APIEndpoint  # pylint: disable=unused-import
import zoe_api.exceptions


class LoginAPI(RequestHandler):
    """The Login API endpoint."""

    def initialize(self, **kwargs):
        """Initializes the request handler."""
        self.api_endpoint = kwargs['api_endpoint']  # type: APIEndpoint

    def set_default_headers(self):
        """Set up the headers for enabling CORS."""
        manage_cors_headers(self)

    @catch_exceptions
    def options(self):
        """Needed for CORS."""
        self.set_status(204)
        self.finish()

    @catch_exceptions
    def get(self):
        """HTTP GET method."""
        uid, role = get_auth(self)

        cookie_val = uid + '.' + role

        self.set_secure_cookie('zoe', cookie_val)

        ret = {
            'uid': uid,
            'role': role
        }

        self.write(ret)

    def data_received(self, chunk):
        """Not implemented as we do not use stream uploads"""
        pass


class UserCollectionAPI(RequestHandler):
    """The User collection API endpoint."""

    def initialize(self, **kwargs):
        """Initializes the request handler."""
        self.api_endpoint = kwargs['api_endpoint']  # type: APIEndpoint

    def set_default_headers(self):
        """Set up the headers for enabling CORS."""
        manage_cors_headers(self)

    @catch_exceptions
    def options(self):
        """Needed for CORS."""
        self.set_status(204)
        self.finish()

    @catch_exceptions
    def get(self):
        """HTTP GET method."""
        uid, role = get_auth(self)

        filt_dict = {}
        users = self.api_endpoint.user_list(uid, role, **filt_dict)

        self.write(dict([(u.id, u.serialize()) for u in users]))

    def data_received(self, chunk):
        """Not implemented as we do not use stream uploads"""
        pass


class UserAPI(RequestHandler):
    """The Login API endpoint."""

    def initialize(self, **kwargs):
        """Initializes the request handler."""
        self.api_endpoint = kwargs['api_endpoint']  # type: APIEndpoint

    def set_default_headers(self):
        """Set up the headers for enabling CORS."""
        manage_cors_headers(self)

    @catch_exceptions
    def options(self):
        """Needed for CORS."""
        self.set_status(204)
        self.finish()

    @catch_exceptions
    def get(self, user_name):
        """HTTP GET method."""
        uid, role = get_auth(self)

        user = self.api_endpoint.user_by_username(uid, role, user_name)

        self.write(user.serialize())

    @catch_exceptions
    def put(self, user_name):
        """Update user information"""
        uid, role = get_auth(self)

        try:
            data = tornado.escape.json_decode(self.request.body)
        except ValueError:
            raise zoe_api.exceptions.ZoeRestAPIException('Error decoding JSON data')

        self.api_endpoint.user_update(uid, role, user_name, data)

    def data_received(self, chunk):
        """Not implemented as we do not use stream uploads"""
        pass
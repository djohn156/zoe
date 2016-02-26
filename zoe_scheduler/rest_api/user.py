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

import time

from werkzeug.exceptions import BadRequest
from flask_restful import Resource, request

from zoe_lib.exceptions import ZoeException, ZoeRestAPIException
from zoe_scheduler.rest_api.utils import catch_exceptions
from zoe_scheduler.state.manager import StateManager
from zoe_scheduler.platform_manager import PlatformManager
from zoe_scheduler.rest_api.auth.authentication import authenticate
from zoe_scheduler.rest_api.auth.authorization import is_authorized
from zoe_scheduler.state.user import User
from zoe_scheduler.config import singletons


class UserAPI(Resource):
    """
    :type state: StateManager
    :type platform: PlatformManager
    """
    def __init__(self, **kwargs):
        self.state = kwargs['state']
        self.platform = kwargs['platform']

    @catch_exceptions
    def get(self, user_id):
        start_time = time.time()
        calling_user = authenticate(request, self.state)

        u = self.state.get_one('user', id=user_id)
        if u is None:
            raise ZoeRestAPIException('No such user', 404)

        is_authorized(calling_user, u, 'get')

        d = u.to_dict(checkpoint=False)
        singletons['metric'].metric_api_call(start_time, 'user', 'get', calling_user)
        return d, 200

    @catch_exceptions
    def delete(self, user_id):
        start_time = time.time()
        calling_user = authenticate(request, self.state)

        user = self.state.get_one('user', id=user_id)
        if user is None:
            raise ZoeRestAPIException('No such user', 404)

        is_authorized(calling_user, user, 'delete')

        apps = self.state.get('application', owner=user)
        if len(apps) > 0:
            raise ZoeRestAPIException('User has {} applications defined, cannot delete'.format(len(apps)))

        self.platform.kill_gateway_container(user)
        self.platform.remove_user_network(user)

        self.state.delete('user', user_id)
        self.state.state_updated()

        singletons['metric'].metric_api_call(start_time, 'user', 'delete', calling_user)
        return '', 204


class UserCollectionAPI(Resource):
    """
    :type state: StateManager
    :type platform: PlatformManager
    """
    def __init__(self, **kwargs):
        self.state = kwargs['state']
        self.platform = kwargs['platform']

    @catch_exceptions
    def post(self):
        """
        Create a new user
        :return:
        """
        start_time = time.time()
        calling_user = authenticate(request, self.state)

        try:
            data = request.get_json()
        except BadRequest:
            raise ZoeRestAPIException('Error decoding JSON data')

        user = User(self.state)
        try:
            user.from_dict(data, checkpoint=False)
        except ZoeException as e:
            raise ZoeRestAPIException(e.value)

        is_authorized(calling_user, user, 'create')

        if len(self.state.get('user', name=user.name)) > 0:
            raise ZoeRestAPIException('Email already registered')

        user.set_password(data['password'])

        user.id = self.state.gen_id()
        self.state.new('user', user)

        self.platform.create_user_network(user)

        self.platform.start_gateway_container(user)

        self.state.state_updated()

        singletons['metric'].metric_api_call(start_time, 'user', 'post', calling_user)
        return {"user_id": user.id}, 201

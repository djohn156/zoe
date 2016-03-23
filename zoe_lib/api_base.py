"""
This package contains the Zoe library, with modules used by more than one of the Zoe components. This library can also be used to write new clients for Zoe.
"""
import requests
import requests.exceptions

from zoe_lib.version import ZOE_API_VERSION
from zoe_lib.exceptions import ZoeAPIException


class ZoeAPIBase:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password

    def _rest_get(self, path):
        """
        :type path: str
        :rtype: (dict, int)
        """
        url = self.url + '/api/' + ZOE_API_VERSION + path
        try:
            r = requests.get(url, auth=(self.user, self.password))
        except requests.exceptions.Timeout:
            raise ZoeAPIException('HTTP connection timeout')
        except requests.exceptions.HTTPError:
            raise ZoeAPIException('Invalid HTTP response')
        except requests.exceptions.ConnectionError as e:
            raise ZoeAPIException('Connection error: {}'.format(e))

        try:
            data = r.json()
        except ValueError:
            data = None
        return data, r.status_code

    def _rest_post(self, path, payload):
        """
        :type path: str
        :rtype: (dict, int)
        """
        url = self.url + '/api/' + ZOE_API_VERSION + path
        try:
            r = requests.post(url, auth=(self.user, self.password), json=payload)
        except requests.exceptions.Timeout:
            raise ZoeAPIException('HTTP connection timeout')
        except requests.exceptions.HTTPError:
            raise ZoeAPIException('Invalid HTTP response')
        except requests.exceptions.ConnectionError as e:
            raise ZoeAPIException('Connection error: {}'.format(e))

        try:
            data = r.json()
        except ValueError:
            data = None
        return data, r.status_code

    def _rest_delete(self, path):
        """
        :type path: str
        :rtype: (dict, int)
        """
        url = self.url + '/api/' + ZOE_API_VERSION + path
        try:
            r = requests.delete(url, auth=(self.user, self.password))
        except requests.exceptions.Timeout:
            raise ZoeAPIException('HTTP connection timeout')
        except requests.exceptions.HTTPError:
            raise ZoeAPIException('Invalid HTTP response')
        except requests.exceptions.ConnectionError as e:
            raise ZoeAPIException('Connection error: {}'.format(e))

        try:
            data = r.json()
        except ValueError:
            data = None
        return data, r.status_code
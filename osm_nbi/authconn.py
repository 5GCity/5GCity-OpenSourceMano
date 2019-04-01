# -*- coding: utf-8 -*-

"""
Authconn implements an Abstract class for the Auth backend connector
plugins with the definition of the methods to be implemented.
"""

__author__ = "Eduardo Sousa <esousa@whitestack.com>"
__date__ = "$27-jul-2018 23:59:59$"

from http import HTTPStatus


class AuthException(Exception):
    """
    Authentication error.
    """
    def __init__(self, message, http_code=HTTPStatus.UNAUTHORIZED):
        self.http_code = http_code
        Exception.__init__(self, message)


class AuthconnException(Exception):
    """
    Common and base class Exception for all authconn exceptions.
    """
    def __init__(self, message, http_code=HTTPStatus.UNAUTHORIZED):
        Exception.__init__(message)
        self.http_code = http_code


class AuthconnConnectionException(AuthconnException):
    """
    Connectivity error with Auth backend.
    """
    def __init__(self, message, http_code=HTTPStatus.BAD_GATEWAY):
        AuthconnException.__init__(self, message, http_code)


class AuthconnNotSupportedException(AuthconnException):
    """
    The request is not supported by the Auth backend.
    """
    def __init__(self, message, http_code=HTTPStatus.NOT_IMPLEMENTED):
        AuthconnException.__init__(self, message, http_code)


class AuthconnNotImplementedException(AuthconnException):
    """
    The method is not implemented by the Auth backend.
    """
    def __init__(self, message, http_code=HTTPStatus.NOT_IMPLEMENTED):
        AuthconnException.__init__(self, message, http_code)


class AuthconnOperationException(AuthconnException):
    """
    The operation executed failed.
    """
    def __init__(self, message, http_code=HTTPStatus.INTERNAL_SERVER_ERROR):
        AuthconnException.__init__(self, message, http_code)


class Authconn:
    """
    Abstract base class for all the Auth backend connector plugins.
    Each Auth backend connector plugin must be a subclass of
    Authconn class.
    """
    def __init__(self, config):
        """
        Constructor of the Authconn class.

        Note: each subclass

        :param config: configuration dictionary containing all the
        necessary configuration parameters.
        """
        self.config = config

    def authenticate_with_user_password(self, user, password):
        """
        Authenticate a user using username and password.

        :param user: username
        :param password: password
        :return: an unscoped token that grants access to project list
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def authenticate_with_token(self, token, project=None):
        """
        Authenticate a user using a token. Can be used to revalidate the token
        or to get a scoped token.

        :param token: a valid token.
        :param project: (optional) project for a scoped token.
        :return: return a revalidated token, scoped if a project was passed or
        the previous token was already scoped.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def validate_token(self, token):
        """
        Check if the token is valid.

        :param token: token to validate
        :return: dictionary with information associated with the token. If the
        token is not valid, returns None.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def revoke_token(self, token):
        """
        Invalidate a token.

        :param token: token to be revoked
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def get_project_list(self, token):
        """
        Get all the projects associated with a user.

        :param token: valid token
        :return: list of projects
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def get_role_list(self, token):
        """
        Get role list for a scoped project.

        :param token: scoped token.
        :return: returns the list of roles for the user in that project. If
        the token is unscoped it returns None.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def create_user(self, user, password):
        """
        Create a user.

        :param user: username.
        :param password: password.
        :raises AuthconnOperationException: if user creation failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def change_password(self, user, new_password):
        """
        Change the user password.

        :param user: username.
        :param new_password: new password.
        :raises AuthconnOperationException: if user password change failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def delete_user(self, user):
        """
        Delete user.

        :param user: username.
        :raises AuthconnOperationException: if user deletion failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def create_role(self, role):
        """
        Create a role.

        :param role: role name.
        :raises AuthconnOperationException: if role creation failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def delete_role(self, role):
        """
        Delete a role.

        :param role: role name.
        :raises AuthconnOperationException: if user deletion failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def create_project(self, project):
        """
        Create a project.

        :param project: project name.
        :raises AuthconnOperationException: if project creation failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def delete_project(self, project):
        """
        Delete a project.

        :param project: project name.
        :raises AuthconnOperationException: if project deletion failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def assign_role_to_user(self, user, project, role):
        """
        Assigning a role to a user in a project.

        :param user: username.
        :param project: project name.
        :param role: role name.
        :raises AuthconnOperationException: if role assignment failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

    def remove_role_from_user(self, user, project, role):
        """
        Remove a role from a user in a project.

        :param user: username.
        :param project: project name.
        :param role: role name.
        :raises AuthconnOperationException: if role assignment revocation failed.
        """
        raise AuthconnNotImplementedException("Should have implemented this")

from fastapi import Request

from foodie_api.repository import Repository
from foodie_api.settings import ApiSettings


def get_repository(request: Request) -> Repository:
    return request.app.state.repository


def get_settings(request: Request) -> ApiSettings:
    return request.app.state.settings

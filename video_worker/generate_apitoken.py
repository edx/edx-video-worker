"""
Generates authorized Video Pipeline and VAL token.

"""

import ast
import logging
import os
import requests

from video_worker.utils import get_config

"""Disable insecure warning for requests lib"""
requests.packages.urllib3.disable_warnings()


settings = get_config()


logger = logging.getLogger(__name__)


def veda_tokengen():
    """
    Gen and authorize a VEDA API token
    """
    # Generate Token
    payload = {'grant_type': 'client_credentials'}
    veda_token_response = requests.post(
        settings['veda_token_url'] + '/',
        params=payload,
        auth=(
            settings['veda_client_id'],
            settings['veda_secret_key']
        ),
        timeout=settings['global_timeout']
    )

    if veda_token_response.status_code != 200:
        logger.error('VEDA Token Generate')
        return

    veda_token = ast.literal_eval(veda_token_response.text)['access_token']

    # Authorize token
    """
    This is based around the VEDA "No Auth Server" hack

    NOTE: After much screwing around, I couldn't get nginx to pass
    the auth headers, so I'm moving to token auth

    **it's shit, and needs a rewrite. see api.py in veda-django
    """
    payload = {'data': veda_token}
    veda_auth_response = requests.post(
        settings['veda_auth_url'] + '/',
        data=payload
    )

    if veda_auth_response.status_code != 200:
        logger.error('VEDA Token Authorization')
        return

    return veda_auth_response.text.strip()


def val_tokengen():
    """
    Gen and authorize a VAL API token
    """
    payload = {
        'grant_type': 'password',
        'client_id': settings['val_client_id'],
        'client_secret': settings['val_secret_key'],
        'username': settings['val_username'],
        'password': settings['val_password']
    }

    response = requests.post(settings['val_token_url'] + '/', data=payload, timeout=settings['global_timeout'])

    if response.status_code != 200:
        logger.error('Token Gen Fail: VAL - Check VAL Config')
        return

    return ast.literal_eval(response.text)['access_token']

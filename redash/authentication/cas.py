import logging
from urllib.parse import urljoin

from flask import Blueprint, flash, redirect, request, session, url_for
from flask_login import login_user
from cas import CASClient

from redash import models
from redash.authentication import (
    create_and_login_user,
    get_next_path,
    logout_and_redirect_to_index,
)
from redash.authentication.org_resolving import current_org
from redash.handlers.base import org_scoped_rule

logger = logging.getLogger("cas_auth")

blueprint = Blueprint("cas_auth", __name__)


def verify_user(org, username):
    """Verify if user is allowed to authenticate."""
    if org.is_public:
        return True

    if org.has_user(username):
        return True

    # TODO: Fallback. should be False in the future, but for now, we allow to accept users in status of pending
    return True


def get_cas_client(org):
    """Create and configure CAS client based on org settings."""
    cas_server_url = org.get_setting("auth_cas_server_url")
    service_url = url_for(".cas_callback", org_slug=org.slug, _external=True)
    version = org.get_setting("auth_cas_protocol_version", 2)

    return CASClient(
        version=version,
        server_url=cas_server_url,
        service_url=service_url
    )


@blueprint.route(org_scoped_rule("/cas/login"))
def cas_login(org_slug=None):
    """Initiate CAS login flow."""
    if not current_org.get_setting("auth_cas_enabled"):
        logger.error("CAS Login is not enabled for org: %s", org_slug)
        return redirect(url_for("redash.index", org_slug=org_slug))

    next_path = request.args.get("next", url_for("redash.index", org_slug=org_slug))
    session["next_url"] = next_path

    cas_client = get_cas_client(current_org)
    login_url = cas_client.get_login_url()
    logger.info("Generated CAS login URL: %s", login_url)

    return redirect(login_url)


@blueprint.route(org_scoped_rule("/cas/callback"))
def cas_callback(org_slug=None):
    """Handle CAS authentication response."""
    if not current_org.get_setting("auth_cas_enabled"):
        logger.error("CAS Login is not enabled for org: %s", org_slug)
        return redirect(url_for("redash.index", org_slug=org_slug))

    ticket = request.args.get("ticket")
    if not ticket:
        logger.error("No ticket parameter in CAS callback for org: %s", org_slug)
        flash("CAS authentication failed. No ticket provided.")
        return redirect(url_for("redash.login", org_slug=org_slug))

    cas_client = get_cas_client(current_org)

    try:
        username, attributes, pgtiou = cas_client.verify_ticket(ticket)
        logger.info("CAS ticket verification result: username=%s, attributes=%s, pgtiou=%s", username, attributes, pgtiou)
    except Exception as e:
        logger.error("Error verifying CAS ticket for org: %s. Error: %s", org_slug, str(e))
        flash("CAS authentication failed. Please try again.")
        return redirect(url_for("redash.login", org_slug=org_slug))

    if not username:
        logger.error("Failed to verify CAS ticket for org: %s", org_slug)
        flash("CAS authentication failed. Invalid ticket.")
        return redirect(url_for("redash.login", org_slug=org_slug))

    if not verify_user(current_org, username):
        logger.warning(
            "Unauthorized login attempt: username=%s, org=%s",
            username,
            current_org,
        )
        flash("Your CAS account isn't allowed.")
        return redirect(url_for("redash.login", org_slug=org_slug))

    # Extract name from attributes if available
    name = attributes.get("displayName", [username])[0] if attributes else username
    # TODO: Here would be a good place to extract the role from attributes and update the groups accordingly

    user = create_and_login_user(current_org, name, username)
    if user is None:
        logger.error("Failed to create or login user: username=%s, org=%s", username, org_slug)
        return logout_and_redirect_to_index()

    unsafe_next_path = session.get("next_url") or url_for("redash.index", org_slug=org_slug)
    next_path = get_next_path(unsafe_next_path)
    logger.info("Redirecting user to next path: %s", next_path)

    return redirect(next_path)

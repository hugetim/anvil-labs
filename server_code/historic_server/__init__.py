# SPDX-License-Identifier: MIT
# Copyright (c) 2021 anvilistas
import anvil.server
from anvil.tables import app_tables

from ..historic.exceptions import UnregisteredClassError
from ..historic.events import Creation, Change, Termination
from .persistence import save_event_records
from .projection import play

__version__ = "0.0.1"
_classes = {}


def register(cls, name):
    _classes[name] = cls


def play_projectors(projectors):
    if projectors is None:
        return
    for projector in projectors:
        play(projector)


def save_event(event, projectors):
    identifier = save_event_records(
        event, record_duplicates=False, return_identifiers=True
    )[0]
    play_projectors(projectors)
    return identifier


@anvil.server.callable("anvil_labs.historic.save_events")
def save_events(
    events, record_duplicates=False, return_identifiers=False, projectors=None
):
    """Save event records and optionally play all projections

    This is intended for saving batches of events which could be of different
    event_types. e.g. where an app goes offline and later has to send all the
    changes that may have occurred.

    events : list
        of Event instances
    prevent_duplication : bool
        Whether to disallow records where the state is unchanged from previously
    return_identifiers : bool
    projectors : list
        of projector names to play

    Returns
    -------
    None or list
        Depending on the value of return_identifiers
    """
    identifiers = save_event_records(events, record_duplicates, return_identifiers)
    play_projectors(projectors)
    return identifiers if return_identifiers else None


@anvil.server.callable("anvil_labs.historic.create")
def create(obj, projectors=None):
    """Save a new object and optionally play all projections

    Parameters
    ----------
    obj : portable class instance
    projectors : list
        of projector names to play

    Returns
    -------
    str
        The uid of the object
    """
    return save_event(Creation(obj), projectors)


@anvil.server.callable("anvil_labs.historic.update")
def update(obj, projectors=None):
    """Save changes to an object and optionally play all projections

    Parameters
    ----------
    obj : portable class instance
    projectors : list
        of projector names to play

    Returns
    -------
    str
        The uid of the object
    """
    return save_event(Change(obj), projectors)


@anvil.server.callable("anvil_labs.historic.delete")
def delete(obj, projectors=None):
    """Delete an object and optionally play all projections

    Parameters
    ----------
    obj : portable class instance
    projectors : list
        of projector names to play
    """
    event = Termination(obj)
    save_event_records(event, prevent_duplication=True, return_identifiers=False)[0]
    play_projectors(projectors)


@anvil.server.callable("anvil_labs.historic.fetch")
def fetch(object_id, as_at=None):
    """Fetch an object with state at a given point in time

    This will fetch a record from the 'current' projection table and
    deserialize that into a portable class instance.

    Parameters
    ----------
    object_id : str
        The object identifier
    as_at : datetime.datetime
    """
    if as_at is None:
        record = app_tables.current.get(object_id=object_id)
    else:
        raise NotImplementedError

    try:
        cls = _classes[record["object_type"]]
    except KeyError:
        raise UnregisteredClassError(
            f"No {record['object_type']} portable class has been registered."
        )

    try:
        return cls.__restore__(record["state"])
    except AttributeError:
        return cls(**record["state"])

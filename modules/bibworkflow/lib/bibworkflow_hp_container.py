## This file is part of Invenio.
## Copyright (C) 2012 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
from invenio.sqlalchemyutils import db


class HoldingPenContainer(db.Model):
    """
    Class containing three HPItems of a single record plus metadata for
    the record
    """
    __tablename__ = "hpContainers"
    bwo_parent_id = db.Column(db.Integer, nullable=False)
    children = db.Column(db.JSON, default={})
    metadata = db.Column(db.JSON, default={})

    def __init__(self, bwo_parent, children=None, metadata=None):
        # owner="", description="",
        # ISBN=0, invenio_id=0, publisher="", category="", version=0):
        self.bwo_parent_id = bwo_parent.id
        self.children = children
        self.metadata = metadata

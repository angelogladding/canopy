"""A full-stack IndieWeb client."""

import sql
import web
from web import tx


app = web.application("Canopy")
app.mount(web.indieauth.server)
app.wrap(web.indieauth.insert_references)  # XXX move to mount subapp
app.mount(web.micropub.server)
app.mount(web.microsub.reader)
app.mount(web.microsub.server)
app.wrap(web.webmention.insert_references)  # XXX move to mount subapp
app.mount(web.webmention.receiver)
app.mount(web.websub.pub)
app.mount(web.websub.sub)

tmpl = web.templates(__name__)


@app.wrap
def contextualize(handler, app):
    """Contextualize this thread based upon the host of the request."""
    tx.me = tx.request.uri.host
    db = sql.db(f"{tx.me}.db")
    db.define(entries="""entry JSON,
                         published TEXT AS
                             (json_extract(entry, '$.published')) STORED,
                         url TEXT AS
                             (json_extract(entry, '$.url')) STORED""")
    tx.host.db = db
    yield


@app.route(r"")
class Home:
    """."""

    def _get(self):
        try:
            myself = tx.db.select("entries", where="url = '/me'")[0]["entry"]
        except IndexError:
            return tmpl.new()
        entries = tx.db.select("entries, json_tree(entries.entry, '$.name')",
                               where="json_tree.type == 'text'",
                               order="published desc", limit=20)
        return tmpl.home(myself["profile"]["name"], entries)

    def _post(self):
        name = web.form("name").name
        tx.db.insert("entries", entry={"url": "/me",
                                       "published": web.utcnow(),
                                       "profile": {"name": name,
                                                   "url": tx.me}})
        tx.db.insert("entries", entry={"url": "/2020/12/01/hello-canopy",
                                       "published": web.utcnow(),
                                       "name": "Hello Canopy"})
        raise web.SeeOther("/")


@app.route(r"\d{{4}}")
class ArchiveYear:
    """Posts from given year."""

    def _get(self):
        return tx.request.uri  # tmpl.archive.year()


@app.route(r"\d{{4}}/\d{{,2}}")
class ArchiveMonth:
    """Posts from given month."""

    def _get(self):
        return tx.request.uri  # tmpl.archive.month()

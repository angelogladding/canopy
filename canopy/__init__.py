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


def publish_entry(url, entry):
    """Publish an entry and return its permalink."""
    now = web.utcnow()
    url = url.format(dtslug=web.timeslug(now),
                     nameslug=web.textslug(entry.get("name")))
    tx.db.insert("entries", entry=dict(**entry, published=now, url=url))
    return url


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
        publish_entry("/me", {"profile": {"name": name, "url": tx.me}})
        publish_entry("/{{dtslug}}/{{nameslug}}", {"name": "Hello world!"})
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

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
    db.define(posts="""post JSON,
                       published TEXT AS
                           (json_extract(post, '$.published')) STORED,
                       url TEXT AS
                           (json_extract(post, '$.url')) STORED""")
    tx.host.db = db
    yield
    # TODO wrap in template


@app.route(r"")
class Home:
    """."""

    def _get(self):
        # web.tx.request.uri
        try:
            name = tx.db.select("posts", where="url = ?", vals=["/me"])[0]
        except IndexError:
            return tmpl.new()
        name = name["profile"]["name"]
        # recent_public = tx.db.select("entries",
        #                              where="visibility = public",
        #                              order="desc", limit=20)
        # count = tx.db.select("entries", where="visibility = public",
        #                      what="count(*) as c")[0]["c"]
        return tmpl.home(name)  # tmpl.entries(recent_public), count))

    def _post(self):
        name = web.form("name").name
        tx.db.insert("posts", post={"url": "/me", "published": web.utcnow(),
                                    "profile": {"name": name, "url": tx.me}})


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

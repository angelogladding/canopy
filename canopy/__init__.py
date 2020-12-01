"""A full-stack IndieWeb client."""

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
    db = sql.db(f"{tx.request.uri.host}.db")
    db.define(posts="""post BLOB,
                       published TEXT AS
                           (json_extract(post, '$.published')) STORED,
                       url TEXT AS
                           (json_extract(post, '$.url')) STORED""")
    tx.db = db
    yield
    # TODO wrap template


@app.route(r"")
class Home:
    """."""

    def _get(self):
        # web.tx.request.uri
        try:
            name = tx.db.select("posts", where="url = /me")[0]["name"]
        except IndexError:
            return tmpl.new(tx)
        # recent_public = tx.db.select("entries",
        #                              where="visibility = public",
        #                              order="desc", limit=20)
        # count = tx.db.select("entries", where="visibility = public",
        #                      what="count(*) as c")[0]["c"]
        return tmpl.home(name)  # tmpl.entries(recent_public), count))

    def _post(self):
        name = web.form("name").name
        post = {"url": "/me", "published": pendulum.now("UTC"),
                "profile": {"name": name}}
        tx.db.insert("posts", post=json.dumps(post))


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

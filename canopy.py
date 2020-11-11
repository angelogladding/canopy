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

# tmpl = web.templates()


@app.route(r"")
class Home:
    """."""

    def _get(self):
        # recent_public = tx.db.select("entries",
        #                              where="visibility = public",
        #                              order="desc", limit=20)
        # count = tx.db.select("entries", where="visibility = public",
        #                      what="count(*) as c")[0]["c"]
        return "foobar!"  # tmpl.home(tmpl.entries(recent_public), count)


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

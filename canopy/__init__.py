"""A full-stack IndieWeb client."""

import sql
import web
from web import tx


app = web.application("Canopy")
app.mount(web.indieauth.server)
app.mount(web.micropub.server)
app.mount(web.microsub.reader)
app.mount(web.microsub.server)
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


def template(handler, app):
    """Wrap the response in a template."""
    yield
    if tx.response.status.startswith("3"):
        pass
    else:
        tx.response.body = tmpl.template(tx.response.body)


app.wrap(template, "post")
app.wrap(web.indieauth.insert_references, "post")
app.wrap(web.webmention.insert_references, "post")


def load_entry(url):
    """Read an entry and return it with its metadata."""
    return tx.db.select("entries", where="url = ?", vals=[f"/{url}"])[0]


def dump_entry(url, entry):
    """Write an entry and return its permalink."""
    now = web.utcnow()
    url = url.format(dtslug=web.timeslug(now),
                     nameslug=web.textslug(entry.get("name", "")))
    tx.db.insert("entries", entry=dict(**entry, author=load_entry("me"),
                                       published=now, url=url))
    return url


@app.route(r"")
class Home:
    """."""

    def _get(self):
        try:
            myself = load_entry("me")["entry"]
        except IndexError:
            return tmpl.new()
        entries = tx.db.select("entries, json_tree(entries.entry, '$.name')",
                               where="json_tree.type == 'text'",
                               order="published desc", limit=20)
        return tmpl.home(myself["profile"]["name"], entries)

    def _post(self):
        name = web.form("name").name
        dump_entry("/about", {"profile": {"name": name, "url": tx.me}})
        dump_entry("/{dtslug}/{nameslug}", {"name": "Hello world!"})
        raise web.SeeOther("/")


@app.route(r"about")
class About:
    """."""

    def _get(self):
        myself = load_entry("me")["entry"]
        return tmpl.about(myself["profile"])


@app.route(r"\d{{4}}")
class ArchiveYear:
    """Entries from given year."""

    def _get(self):
        return tx.request.uri  # tmpl.archive.year()


@app.route(r"\d{{4}}/\d{{,2}}")
class ArchiveMonth:
    """Entries from given month."""

    def _get(self):
        return tx.request.uri  # tmpl.archive.month()


@app.route(r".*")
class Entry:
    """An individual entry."""

    def _get(self):
        entry = load_entry(tx.request.uri.path)["entry"]
        return tmpl.entry(entry)

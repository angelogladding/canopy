"""A full-stack IndieWeb client."""

import hmac
import random

import Crypto.Random
import scrypt
import sql
import web
from web import tx


app = web.application("Canopy", year=r"\d{4}", month=r"\d{2}", day=r"\d{2}",
                      seconds=web.nb60_re + r"{,4}", slug=r"[\w_]+")
app.mount(web.indieauth.server)
app.mount(web.micropub.server)
app.mount(web.microsub.reader)
app.mount(web.microsub.server)
app.mount(web.webmention.receiver)
app.mount(web.websub.pub)
app.mount(web.websub.sub)
tmpl = web.templates(__name__, globals={"tx": tx})


@app.wrap
def contextualize(handler, app):
    """Contextualize this thread based upon the host of the request."""
    tx.me = tx.request.uri.host
    db = sql.db(f"{tx.me}.db")
    db.define(entries="""entry JSON,
                         published TEXT AS
                             (json_extract(entry, '$.published')) STORED,
                         url TEXT AS
                             (json_extract(entry, '$.url')) STORED""",
              credentials="""created DATETIME NOT NULL
                                 DEFAULT CURRENT_TIMESTAMP,
                             salt BLOB, scrypt_hash BLOB""")
    tx.host.db = db
    yield


@app.wrap
def template(handler, app):
    """Wrap the response in a template."""
    yield
    if tx.response.headers.content_type == "text/html":
        tx.response.body = tmpl.template(tx.response.body)


app.wrap(web.indieauth.insert_references, "post")
app.wrap(web.webmention.insert_references, "post")


link_headers = {"authorization_endpoint": "sign-in",
                "token_endpoint": "token",
                "webmention": "mentions",
                "micropub": "micropub",
                "hub": "hub",
                "self": ""}


def load_entry(url):
    """Read an entry and return it with its metadata."""
    return tx.db.select("entries", where="url = ?", vals=[url])[0]


def dump_entry(url, entry):
    """Write an entry and return its permalink."""
    now = web.utcnow()
    url = url.format(dtslug=web.timeslug(now),
                     nameslug=web.textslug(entry.get("name", "")))
    try:
        author = load_entry("about")["entry"]["profile"]
    except IndexError:  # TODO handle first post
        author = entry["profile"]
    tx.db.insert("entries", entry=dict(**entry, published=now, url=url,
                                       author=author))
    # TODO tx.db.snapshot()
    return url


@app.route(r"")
class Home:
    """."""

    def _head(self):
        self.emit_headers()
        return ""

    def _get(self):
        self.emit_headers()
        try:
            myself = load_entry("about")["entry"]
        except IndexError:
            return tmpl.new()
        entries = tx.db.select("entries, json_tree(entries.entry, '$.name')",
                               where="json_tree.type == 'text'",
                               order="published desc", limit=20)
        return tmpl.home(myself["profile"]["name"], entries)

    def emit_headers(self):
        """Emit homepage headers for HEAD and GET."""
        for rel, path in link_headers.items():
            web.header("Link", f'https://<{tx.request.uri.host}/{path}>;'
                       'rel="{rel}"', add=True)

    def _post(self):
        name = web.form("name").name
        dump_entry("about", {"profile": {"name": name, "url": tx.me}})
        dump_entry("{dtslug}/{nameslug}", {"name": "Hello world!"})
        return tmpl.welcome(reset_passphrase())


def reset_passphrase():
    """Set a new randomly-generated passphrase and return it."""
    passphrase_words = set()
    while len(passphrase_words) < 7:
        passphrase_words.add(random.choice(web.wordlist))
    passphrase = "".join(passphrase_words)
    salt = Crypto.Random.get_random_bytes(64)
    scrypt_hash = scrypt.hash(passphrase, salt)
    tx.insert("credentials", salt=salt, scrypt_hash=scrypt_hash)
    # TODO tx.db.snapshot()
    return passphrase


def verify_passphrase(passphrase):
    """Verify given passphrase."""
    credentials = tx.db.select("credentials", order="created DESC")[0]
    scrypt_hash = scrypt.hash(passphrase, credentials["salt"])
    return hmac.compare_digest(scrypt_hash, credentials["scrypt_hash"])


@app.route(r"about")
class About:
    """."""

    def _get(self):
        myself = load_entry("about")["entry"]
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


@app.route(r"{year}/{month}/{day}/{seconds}(/{slug})?")
class Entry:
    """An individual entry."""

    def _get(self):
        entry = load_entry(tx.request.uri.path)["entry"]
        return tmpl.entry(entry)


@app.route(r"sign-in")
class SignIn:
    """Sign in as the owner of the site."""

    def _get(self):
        return tmpl.sign_in()

    def _post(self):
        passphrase = web.form("passphrase").passphrase
        tx.user.session["baz"] = "foo"
        print(passphrase)
        raise web.SeeOther("/")

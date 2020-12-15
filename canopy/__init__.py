"""A full-stack IndieWeb client."""

import hmac
import random

import Crypto.Random
import scrypt
import sql
import web
from web import tx


app = web.application("Canopy", static=__name__, year=r"\d{4}", month=r"\d{2}",
                      day=r"\d{2}", seconds=web.nb60_re + r"{,4}",
                      slug=r"[\w_]+", person=r".+", event=".+")
tmpl = web.templates(__name__)


def load_resource(url):
    """Read a resource and return it with its metadata."""
    return tx.db.select("resources", where="url = ?", vals=[url],
                        order="published DESC", limit=1)[0]


def dump_resource(url, resource):
    """Write a resource and return its permalink."""
    now = web.utcnow()
    url = url.format(dtslug=web.timeslug(now),
                     nameslug=web.textslug(resource.get("name", "")))
    try:
        author = load_resource("about")["resource"]
    except IndexError:  # TODO bootstrap first post with first post
        author = dict(resource)
    author.pop("type")
    tx.db.insert("resources", resource=dict(**resource, published=now,
                                            url=url, author=author))
    # TODO tx.db.snapshot()
    return url


@app.route(r"")
class Home:
    """."""

    def _get(self):
        try:
            owner = load_resource("about")["resource"]
        except IndexError:
            return tmpl.new()
        resources = tx.db.select("resources, "
                                 "json_tree(resources.resource, '$.name')",
                                 where="json_tree.type == 'text'",
                                 order="published desc", limit=20)
        return tmpl.home(owner["name"], resources)

    def _post(self):
        name = web.form("name").name
        dump_resource("about", {"type": "card", "name": name, "uid": tx.owner})
        dump_resource("{dtslug}/{nameslug}", {"type": "entry",
                                              "name": "Hello world!"})
        return tmpl.welcome(reset_passphrase())


def reset_passphrase():
    """Set a new randomly-generated passphrase and return it."""
    passphrase_words = set()
    while len(passphrase_words) < 7:
        passphrase_words.add(random.choice(web.wordlist))
    passphrase = "".join(passphrase_words)
    salt = Crypto.Random.get_random_bytes(64)
    scrypt_hash = scrypt.hash(passphrase, salt)
    tx.db.insert("credentials", salt=salt, scrypt_hash=scrypt_hash)
    # TODO tx.db.snapshot()
    return passphrase_words


def verify_passphrase(passphrase):
    """Verify given passphrase."""
    credentials = tx.db.select("credentials", order="created DESC")[0]
    scrypt_hash = scrypt.hash(passphrase, credentials["salt"])
    return hmac.compare_digest(scrypt_hash, credentials["scrypt_hash"])


@app.route(r"about")
class About:
    """."""

    def _get(self):
        owner = load_resource("about")["resource"]
        return tmpl.about(owner)

    def _post(self):
        profile = web.form()
        profile["urls"] = profile["urls"].splitlines()
        profile["type"] = "card"
        print(profile)
        dump_resource("about", profile)
        raise web.SeeOther("/about")


@app.route(r"{year}")
class ArchiveYear:
    """Resources from given year."""

    def _get(self):
        return tx.request.uri  # tmpl.archive.year()


@app.route(r"{year}/{month}")
class ArchiveMonth:
    """Resources from given month."""

    def _get(self):
        return tx.request.uri  # tmpl.archive.month()


@app.route(r"{year}/{month}/{day}")
class ArchiveDay:
    """Resources from given day."""

    def _get(self):
        return tx.request.uri  # tmpl.archive.day()


@app.route(r"{year}/{month}/{day}/{seconds}(/{slug})?")
class Entry:
    """An individual entry."""

    mentionable = True

    def _get(self):
        resource = load_resource(tx.request.uri.path)["resource"]
        return tmpl.entry(resource)


@app.route(r"network")
class Network:
    """Your social network."""

    def _get(self):
        resource = load_resource(tx.request.uri.path)["resource"]
        return tmpl.resource(resource)


@app.route(r"network/{person}")
class Person:
    """A person in your network."""

    def _get(self):
        resource = load_resource(tx.request.uri.path)["resource"]
        return tmpl.resource(resource)


@app.route(r"events")
class Calendar:
    """Your event calendar."""

    def _get(self):
        resource = load_resource(tx.request.uri.path)["resource"]
        return tmpl.resource(resource)


@app.route(r"events/{event}")
class Event:
    """An event on your calendar."""

    def _get(self):
        resource = load_resource(tx.request.uri.path)["resource"]
        return tmpl.resource(resource)


@app.route(r"sign-in")
class SignIn:
    """Sign in as the owner of the site."""

    def _get(self):
        return tmpl.sign_in()

    def _post(self):
        # TODO passphrase = web.form("passphrase").passphrase
        tx.user.session["me"] = tx.owner  # FIXME
        # TODO return_to
        raise web.SeeOther("/")


app.mount(web.indieauth.server)
app.mount(web.micropub.server)
app.mount(web.microsub.reader)
app.mount(web.microsub.server)
app.mount(web.webmention.receiver)
app.mount(web.websub.pub)
app.mount(web.websub.sub)


@app.wrap
def contextualize(handler, app):
    """Contextualize this thread based upon the host of the request."""
    db = sql.db(f"{tx.owner}.db")
    db.define(resources="""resource JSON,
                           published TEXT AS
                               (json_extract(resource, '$.published')) STORED,
                           url TEXT AS
                               (json_extract(resource, '$.url')) STORED""",
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
app.wrap(web.micropub.insert_references, "post")
app.wrap(web.webmention.insert_references, "post")
app.wrap(web.websub.insert_references, "post")

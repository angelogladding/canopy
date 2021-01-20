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


@app.route(r"")
class Home:
    """."""

    def _get(self):
        try:
            owner = tx.pub.read("")["resource"]
        except IndexError:
            return tmpl.new()
        return tmpl.home(owner["properties"]["name"], tx.pub.recent_entries())


@app.route(r"about")
class About:
    """."""

    def _get(self):
        return tmpl.about(tx.pub.read("about")["properties"])

    def _post(self):
        profile = web.form()
        profile["urls"] = profile["urls"].splitlines()
        profile["type"] = "card"
        print(profile)
        tx.pub.update("about", profile)
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
        print(tx.request.uri.path)
        resource = tx.pub.read(tx.request.uri.path)
        return tmpl.entry(resource)


@app.route(r"network")
class Network:
    """Your social network."""

    def _get(self):
        resource = tx.pub.read(tx.request.uri.path)
        return tmpl.resource(resource)


@app.route(r"network/{person}")
class Person:
    """A person in your network."""

    def _get(self):
        resource = tx.pub.read(tx.request.uri.path)
        return tmpl.resource(resource)


@app.route(r"events")
class Calendar:
    """Your event calendar."""

    def _get(self):
        resource = tx.pub.read(tx.request.uri.path)
        return tmpl.resource(resource)


@app.route(r"events/{event}")
class Event:
    """An event on your calendar."""

    def _get(self):
        resource = tx.pub.read(tx.request.uri.path)
        return tmpl.resource(resource)


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
    db.define(credentials="""created DATETIME NOT NULL
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


@app.route(r"initialize")
class Initialize:
    """."""

    def _post(self):
        name = web.form("name").name
        uid = str(web.uri(tx.owner))
        tx.pub.create("", {"type": ["h-card"],
                           "properties": {"name": name, "uid": uid,
                                          "url": [uid]}})
        tx.pub.create("{timeslug}/{nameslug}", {"type": ["h-entry"],
                                                "properties":
                                                {"content": "Hello world!"}})
        return tmpl.welcome(reset_passphrase())


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

# canopy :construction:
a full-stack IndieWeb client

Store and display content on your own personal website. Interact richly with other sites.

## Install

[Create a web presence](https://github.com/angelogladding/ghost), install "GitHub Repo" `canopy`, run the canopy application and map it to your installed domain.

## Features

* render profile, pages, media, posts and feeds with semantic markup a la [microformats](https://indieweb.org/microformats)
  * archive source material for [reply contexts](https://indieweb.org/reply-context)
  * moderated threaded discussion using Webmentions with Salmention & Vouch
  * syndicate to third-party aggregators
* store posts:
  * as [queryable JSON](https://www.sqlite.org/json1.html) in SQLite database
    * [full-text search](https://www.sqlite.org/fts5.html)
  * as JSON flat files inside Git repository for change history
* follow by subscribing and publish to subscribers using WebSub
* sign in to third-party applications using IndieAuth
  * leverage third-party Micropub editors
  * leverage third-party Microsub readers
* import/export tools
  * syndicate/backfeed to/from Twitter/Github/Facebook
  * backup/restore to/from local/remote storage

## Third-party Hosts

* **[Canopy Garden](https://canopy.garden)** `cnpy.gdn` operated by *[Angelo Gladding](https://angelogladding.com)*

*For inclusion here create an issue pointing to your public suffix domain included on the HSTS preload.*

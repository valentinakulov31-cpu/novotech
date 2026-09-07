# Catalog SEO

Public routes are `/product/<slug>`, `/group/<slug>` and `/brand/<slug>`.
The catalog root remains `/catalog`. External canonical URLs are rejected.
Generated titles and descriptions identify Novateh; supplier descriptions are
preserved as product content and are not reused for marketing metadata.
Keep SEO override columns empty when importing supplier data. Custom overrides
are still supported for deliberately written, site-specific metadata.

## Reset imported overrides

Preview (no writes):

```sh
python manage.py reset_catalog_seo
```

After making a database backup, apply with a new, private backup filename:

```sh
python manage.py reset_catalog_seo --apply --backup /private-backups/catalog-seo.json
```

Only `seo_title`, `seo_h1`, `seo_description`, `seo_keywords` and
`seo_canonical_url` on Product and Group are reset. `seo_robots`, visibility,
descriptions, characteristics, prices, photos, certificates and relationships
are unchanged. The command locks selected rows, exclusively creates and fsyncs
the backup before updating, and invalidates the shared catalog cache.
Re-running after cleanup is a no-op. Never put the backup in media/static.

The JSON backup is NOT a Django fixture: do not use `loaddata`. For a targeted
rollback, read `records` and restore only the five names in `fields`, using
Product/Group primary keys and an atomic transaction. Review intervening edits
first, and invalidate the catalog cache afterward. A full database snapshot is
the separate disaster-recovery fallback, not the normal metadata rollback.

## Verification

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test shop.tests_seo_cleanup shop.tests_seo_infra shop.tests_geo_seo shop.tests_catalog_media shop.tests_catalog_visibility
```

2026-09-07: 40 targeted tests passed; no migration drift. The full `shop.tests`
suite retains its existing four search/facet failures and the undefined
`cleaned_html` variable in `tests_admin_ui`. These are not SEO regressions.

## Yandex products

Technical SEO does not automatically connect a merchant feed. At the audit,
all 287 public products had zero prices (price on request). Do not publish zero
as a free offer, fabricate prices, reviews or ratings. Real prices and compliant
photos are prerequisites for a useful merchant feed; its acceptance must be
verified separately in the Yandex merchant account.

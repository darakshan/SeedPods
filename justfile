# Seed Nuggets — build
# Requires: python3, just  (brew install just)

root := justfile_directory()

# Rebuild the full site from nuggets/
build:
    python3 {{root}}/src/build.py

# Rebuild a single nugget (e.g. just build-nugget 001)
build-nugget nugget:
    python3 {{root}}/src/build.py --nugget {{nugget}}

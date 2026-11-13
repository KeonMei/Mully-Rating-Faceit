"""The website's backend.

api.py  - GET /api/rating?player=<nickname or link>&matches=30
          returns a player's Mully Rating as JSON. On Vercel it runs as
          a Python function (api/rating.py); locally scripts/serve_web.py
          serves it together with the pages in public/.
"""

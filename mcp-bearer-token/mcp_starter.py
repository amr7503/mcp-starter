import asyncio
from typing import Annotated
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import INVALID_PARAMS
from pydantic import Field

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# --- Load environment variables ---
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"
assert SPOTIFY_CLIENT_ID is not None, "Please set SPOTIFY_CLIENT_ID in your .env file"
assert SPOTIFY_CLIENT_SECRET is not None, "Please set SPOTIFY_CLIENT_SECRET in your .env file"

# --- Setup Spotify client ---
auth_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
)
sp = spotipy.Spotify(auth_manager=auth_manager)

# --- Auth Provider for MCP Server ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None

# --- Initialize MCP server ---
mcp = FastMCP("Spotify Playlist Maker MCP Server", auth=SimpleBearerAuthProvider(TOKEN))

# --- Required MCP validate tool ---
@mcp.tool
async def validate() -> str:
    # Returns your contact or identifier for Puch AI validation
    return MY_NUMBER

# --- Spotify Playlist Maker Tool ---
@mcp.tool(description="Generate Spotify track suggestions based on mood or genre prompt")
async def spotify_playlist_maker(
    prompt: Annotated[str, Field(description="Description of desired playlist mood, genre, or theme")]
) -> str:
    if not prompt or prompt.strip() == "":
        raise McpError(ErrorData(code=INVALID_PARAMS, message="Prompt cannot be empty."))

    results = sp.search(q=prompt, limit=20, type="track")
    tracks = results.get('tracks', {}).get('items', [])
    if not tracks:
        return f"No tracks found for prompt: {prompt}"

    playlist_lines = [f"Spotify Playlist Tracks for prompt: '{prompt}':\n"]
    for track in tracks:
        name = track.get("name")
        artists = ", ".join(artist["name"] for artist in track.get("artists", []))
        url = track.get("external_urls", {}).get("spotify", "")
        playlist_lines.append(f"{name} by {artists}\n{url}")

    return "\n\n".join(playlist_lines)

# --- Run MCP server ---
async def main():
    print("🚀 Starting Spotify Playlist Maker MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())

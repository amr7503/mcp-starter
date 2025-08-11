import asyncio
import os
from typing import Annotated
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import INVALID_PARAMS
from pydantic import Field
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

assert TOKEN is not None
assert MY_NUMBER is not None
assert SPOTIFY_CLIENT_ID is not None
assert SPOTIFY_CLIENT_SECRET is not None

auth_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
)
sp = spotipy.Spotify(auth_manager=auth_manager)

class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token
    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(token=token, client_id="puch-client", scopes=["*"], expires_at=None)
        return None

mcp = FastMCP("Spotify Playlist Maker MCP Server", auth=SimpleBearerAuthProvider(TOKEN))

@mcp.tool
async def validate() -> str:
    return MY_NUMBER


from textwrap import dedent

@mcp.tool
async def about() -> dict[str, str]:
    server_name = "Spotify Playlist Maker MCP"
    server_description = dedent("""
    This MCP server helps you create curated Spotify playlists using natural language prompts.
    Describe your mood, a genre, or an activity, and get a list of Spotify tracks instantly, each with direct links.
    The server uses secure authentication and supports integration with Puch AI for easy playlist building and sharing.
    Mage by team Neural Chakra from Siksha 'O' Anusandhan University 
    """)
    return {
        "name": server_name,
        "description": server_description
    }

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8086))
    asyncio.run(mcp.run_async("streamable-http", host="0.0.0.0", port=port))

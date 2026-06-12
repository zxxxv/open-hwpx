"""open-hwpx MCP 서버 (선택적 — ``pip install open-hwpx[mcp]``).

:mod:`open_hwpx.agent` 의 도구 함수를 그대로 MCP 도구로 노출한다. **같은 함수가
직접 SDK tool-use 에도 쓰이므로** 한 번 짠 도구를 두 경로에서 공유한다.

실행::

    open-hwpx-mcp                 # stdio 트랜스포트로 서버 기동
    python -m open_hwpx.mcp_server

직접 만드는 에이전트 서비스라면 MCP 없이 :mod:`open_hwpx.agent` 함수를 바로 호출해도 된다.
"""

from __future__ import annotations

from . import agent


def build_server():
    """agent.TOOLS 를 등록한 FastMCP 서버를 만든다(``mcp`` 패키지 필요)."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - 선택 의존성 안내
        raise ImportError(
            "MCP 서버에는 'mcp' 패키지가 필요합니다. `pip install open-hwpx[mcp]` 로 설치하세요."
        ) from exc

    server = FastMCP("open-hwpx")
    for fn in agent.TOOLS:
        server.tool()(fn)
    return server


def main() -> None:  # pragma: no cover - 프로세스 진입점
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()

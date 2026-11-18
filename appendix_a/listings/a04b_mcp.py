import asyncio

from appendix_a.mcp_server import build_server

server = build_server()
tools = asyncio.run(server.list_tools())
print([tool.name for tool in tools])
result = asyncio.run(
    server.call_tool("facade_cost_movement", {}))
for line in result.content[0].text.splitlines()[1:4]:
    print(line[:60])

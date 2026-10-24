import asyncio, pathlib
from playwright.async_api import async_playwright
svg = pathlib.Path("linde-asu-pfd-v1.svg").resolve()
html = f'<html><head><meta charset="utf-8"><style>body{{margin:0;background:#fff}}img{{width:1680px}}</style></head><body><img src="file://{svg}"></body></html>'
pathlib.Path("render.html").write_text(html)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/meta-chromium/chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1720, "height": 1250})
        await pg.goto("file://" + str(pathlib.Path("render.html").resolve()))
        await pg.wait_for_timeout(600)
        await pg.screenshot(path="linde-asu-pfd-v1.png")
        pdf_page = await b.new_page()
        await pdf_page.goto("file://" + str(pathlib.Path("render.html").resolve()))
        await pdf_page.wait_for_timeout(400)
        await pdf_page.pdf(path="linde-asu-pfd-v1.pdf", width="420mm", height="297mm", print_background=True)
        await b.close()
asyncio.run(main())
print("rendered")

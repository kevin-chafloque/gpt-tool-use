import os
import asyncio
from playwright.async_api import async_playwright

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatgpt_profile")

class ChatGPTBrowser:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.main_chat_url = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.page = self.browser.pages[0] if len(self.browser.pages) > 0 else await self.browser.new_page()
        await self.reset_chat()

    async def reset_chat(self):
        await self.page.goto("https://chatgpt.com/?model=auto")
        try:
            await self.page.wait_for_selector('#prompt-textarea', timeout=15000)
        except Exception as e:
            await self.page.screenshot(path="debug_error.png")
            raise Exception(f"Failed to find the chat input box. Screenshot saved to 'debug_error.png'. Error: {e}")

    async def stream_message(self, message: str):
        elements_before = await self.page.query_selector_all('div[data-message-author-role="assistant"]')
        count_before = len(elements_before)

        await self.page.fill('#prompt-textarea', message)
        await self.page.press('#prompt-textarea', 'Enter')

        try:
            wait_time = 0
            while wait_time < 30000:
                current_count = len(await self.page.query_selector_all('div[data-message-author-role="assistant"]'))
                if current_count > count_before:
                    break
                await self.page.wait_for_timeout(500)
                wait_time += 500

            if wait_time >= 30000:
                raise Exception("Timeout waiting for assistant message to appear.")
        except Exception as e:
            await self.page.screenshot(path="debug_send.png")
            yield {"type": "final", "content": f"Error: Message didn't send or respond. Details: {e}", "sources": []}
            return

        last_text = ""
        stable_count = 0
        while True:
            await self.page.wait_for_timeout(500)
            elements = await self.page.query_selector_all('div[data-message-author-role="assistant"]')
            if not elements:
                continue

            current_text = await elements[-1].inner_text()

            if current_text == last_text and current_text.strip() != "":
                 stable_count += 1
            else:
                 stable_count = 0

            last_text = current_text

            if stable_count >= 5:
                class_attr = await elements[-1].get_attribute("class")
                is_streaming = "result-streaming" in (class_attr or "")

                stop_btn = await self.page.query_selector('[data-testid="stop-button"]')
                aria_stop = await self.page.query_selector('[aria-label="Stop generating"]')

                stop_visible = await stop_btn.is_visible() if stop_btn else False
                aria_visible = await aria_stop.is_visible() if aria_stop else False

                if not is_streaming and not stop_visible and not aria_visible:
                    break
                else:
                    stable_count = 3

        elements = await self.page.query_selector_all('div[data-message-author-role="assistant"]')
        if not elements:
            yield {"type": "final", "content": "Error: Could not locate the response in the DOM.", "sources": []}
            return

        last_response = elements[-1]

        html_payload = await last_response.evaluate('''
            (el) => {
                let cloned = el.cloneNode(true);

                cloned.querySelectorAll('svg').forEach(x => x.remove());

                let sources = [];
                let refs = cloned.querySelectorAll('.citation, a, button, sup');

                refs.forEach(node => {
                    let isCitation = node.tagName === 'BUTTON' || node.tagName === 'SUP' || (node.classList && node.classList.contains('citation'));
                    let isLink = node.tagName === 'A' && node.href;

                    if (isLink) {
                        let link = node.href;
                        if (link.startsWith('http') && !link.includes('chatgpt.com/c/')) {
                            if (!sources.includes(link)) {
                                sources.push(link);
                            }
                            if (node.classList.length > 2 || node.textContent.length < 25) {
                                isCitation = true;
                            }
                        }
                    }

                    if (isCitation) {
                        if (isLink) {
                            let num = sources.indexOf(node.href) + 1;
                            let span = document.createElement('span');
                            span.textContent = ` [${num}]`;
                            node.parentNode.replaceChild(span, node);
                        } else {
                            node.remove();
                        }
                    }
                });

                cloned.querySelectorAll('details, .search-results').forEach(x => x.remove());

                let markdownEl = cloned.querySelector('.markdown');
                let clean_html = markdownEl ? markdownEl.innerHTML : cloned.innerHTML;

                return {html: clean_html, sources: sources};
            }
        ''')

        from markdownify import markdownify
        final_markdown = markdownify(html_payload["html"], heading_style="ATX").strip()

        yield {"type": "final", "content": final_markdown, "sources": html_payload["sources"]}

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

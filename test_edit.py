from playwright.sync_api import sync_playwright
import time

results = []

def log(msg):
    print(f"[LOG] {msg}")
    results.append(msg)

def test_edit_functionality():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console errors
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        try:
            # Navigate to config page
            log("1. Navigating to http://localhost:3000/config")
            page.goto('http://localhost:3000/config', wait_until='networkidle')
            page.wait_for_timeout(2000)  # Wait for Vue to render

            # Take screenshot of initial state
            page.screenshot(path='/tmp/config_initial.png', full_page=True)
            log("   Screenshot saved to /tmp/config_initial.png")

            # 1. Verify edit buttons appear on each weight row
            log("2. Checking for edit buttons on weight rows")

            # Look for edit buttons - try multiple selectors
            edit_buttons = page.locator('button:has-text("编辑"), button[aria-label*="edit"], .el-icon-edit, [class*="edit"]').all()
            log(f"   Found {len(edit_buttons)} potential edit buttons")

            # More specific - look for action buttons in the table
            action_buttons = page.locator('.el-button--small:has-text("编辑"), .el-button--small:not(.is-text)').all()
            log(f"   Found {len(action_buttons)} small action buttons")

            # Take screenshot to see what's on the page
            page.screenshot(path='/tmp/config_buttons.png')
            log("   Screenshot of buttons saved to /tmp/config_buttons.png")

            # Find edit buttons more precisely - look in the weights table
            edit_btn = page.locator('tr').last.locator('button').first
            if edit_btn.count() > 0:
                log("   Edit button found in table row")

            # Try to find all Edit buttons in the table
            all_buttons_text = page.locator('button').all_text_contents()
            log(f"   All buttons on page: {all_buttons_text}")

            # Find the first weight row's edit button
            # Looking for the edit action button in weight rows
            edit_button_selector = 'table tr td:last-child button, table tr td:nth-child(6) button, .el-table__row button'

            # Check what's actually in the table
            table_html = page.locator('.el-table').inner_html() if page.locator('.el-table').count() > 0 else "No el-table found"
            log(f"   Table exists: {page.locator('.el-table').count() > 0}")

            # Find all buttons in table rows
            table_buttons = page.locator('.el-table__row button').all()
            log(f"   Buttons in table rows: {len(table_buttons)}")

            if len(table_buttons) > 0:
                # Click the first edit button
                first_edit_btn = table_buttons[0]
                btn_text = first_edit_btn.inner_text()
                log(f"   First table button text: '{btn_text}'")

                # Check if there's an edit button (could be icon only)
                edit_btns = [b for b in table_buttons if 'edit' in b.get_attribute('class') or '编辑' in b.inner_text() or b.get_attribute('aria-label')]
                log(f"   Edit buttons found: {len(edit_btns)}")

                if edit_btns:
                    # 2. Click edit button and verify dialog opens
                    log("3. Clicking edit button")
                    edit_btns[0].click()
                    page.wait_for_timeout(1000)

                    # Check if dialog opened
                    dialog_visible = page.locator('.el-dialog, [role="dialog"], .el-message-box').is_visible()
                    log(f"   Dialog opened: {dialog_visible}")

                    if dialog_visible:
                        page.screenshot(path='/tmp/dialog_open.png')
                        log("   Screenshot of dialog saved to /tmp/dialog_open.png")

                        # Get dialog content to verify pre-filled data
                        dialog_title = page.locator('.el-dialog__title').inner_text() if page.locator('.el-dialog__title').count() > 0 else "No title"
                        log(f"   Dialog title: {dialog_title}")

                        # Get form fields in dialog
                        inputs = page.locator('.el-dialog input, .el-dialog .el-input__inner').all()
                        log(f"   Input fields in dialog: {len(inputs)}")

                        if inputs:
                            # Get current values
                            for i, inp in enumerate(inputs):
                                val = inp.input_value() if hasattr(inp, 'input_value') else ""
                                log(f"   Input {i}: '{val}'")

                            # 3. Modify the first input field
                            log("4. Changing display name in first input")
                            first_input = inputs[0]
                            current_val = first_input.input_value()

                            # Clear and type new value
                            first_input.fill("")
                            first_input.type("测试字段名_" + str(int(time.time())))

                            page.wait_for_timeout(500)

                            # 4. Click confirm button in dialog
                            log("5. Clicking confirm button in dialog")
                            confirm_btn = page.locator('.el-dialog__footer button:has-text("确"), .el-dialog__footer .el-button--primary')
                            if confirm_btn.count() > 0:
                                confirm_btn.first.click()
                                page.wait_for_timeout(2000)

                                log("   Confirm button clicked")

                                # 5. Check if row label was updated
                                page.screenshot(path='/tmp/after_confirm.png', full_page=True)
                                log("   Screenshot after confirm saved")

                                # Verify the change took effect (check if new value appears in table)
                                new_value = first_input.input_value() if inputs else ""
                                log(f"   New value entered: {new_value}")

                                # Check if there's a success message
                                success_msg = page.locator('.el-message--success, .el-notification--success').is_visible()
                                log(f"   Success message visible: {success_msg}")

                            else:
                                log("   Confirm button not found, trying other selectors")
                                # Try alternative confirm buttons
                                alt_confirm = page.locator('.el-dialog__footer button:last-child, .el-message-box__btns button:last-child')
                                if alt_confirm.count() > 0:
                                    alt_confirm.first.click()
                                    page.wait_for_timeout(2000)
                                    log("   Alternative confirm button clicked")

                        # 6. Test persistence by refreshing
                        log("6. Refreshing page to test persistence")
                        page.reload(wait_until='networkidle')
                        page.wait_for_timeout(2000)

                        page.screenshot(path='/tmp/after_refresh.png', full_page=True)
                        log("   Screenshot after refresh saved")

                        # Check if the modified value is still there
                        # Look for the modified text in table
                        modified_text = page.locator('.el-table__body').inner_text()
                        log(f"   Table body contains modified text: {'测试字段名' in modified_text}")

                        log("   Persistence check completed")

                    else:
                        log("   ERROR: Dialog did not open after clicking edit button")

            # Report any console errors
            if errors:
                log(f"   Console errors found: {len(errors)}")
                for err in errors[:5]:  # First 5 errors
                    log(f"      - {err[:200]}")
            else:
                log("   No console errors detected")

            log("\n=== TEST COMPLETED ===")

        except Exception as e:
            log(f"ERROR: {str(e)}")
            import traceback
            log(traceback.format_exc())
            page.screenshot(path='/tmp/error_state.png')

        finally:
            browser.close()

    return results

if __name__ == "__main__":
    results = test_edit_functionality()
    print("\n\n=== RESULTS SUMMARY ===")
    for r in results:
        print(r)

# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: 01_startup.spec.ts >> App Startup >> app loads within 2 seconds
- Location: e2e/tests/01_startup.spec.ts:30:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.waitFor: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('[data-testid="sidebar"]') to be visible

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - button "Open Next.js Dev Tools" [ref=e7] [cursor=pointer]:
    - img [ref=e8]
  - alert [ref=e11]
  - generic [ref=e12]:
    - generic [ref=e13]:
      - generic [ref=e14]:
        - img [ref=e15]
        - heading "Shopping Cart" [level=2] [ref=e18]
        - generic [ref=e19]: (0)
      - button [ref=e20] [cursor=pointer]:
        - img [ref=e21]
    - generic [ref=e25]:
      - img [ref=e27]
      - heading "Your cart is empty" [level=3] [ref=e31]
      - paragraph [ref=e32]: Add something to your collection to get started.
      - button "Start Shopping" [ref=e33] [cursor=pointer]
  - generic [ref=e34]:
    - generic [ref=e36]:
      - navigation [ref=e37]:
        - link "Deshio" [ref=e38] [cursor=pointer]:
          - /url: /e-commerce
          - generic [ref=e40]: Deshio
        - link "Search" [ref=e41] [cursor=pointer]:
          - /url: /e-commerce/search
          - img [ref=e42]
          - generic [ref=e45]: Search
        - link "New" [ref=e46] [cursor=pointer]:
          - /url: /e-commerce/products
          - img [ref=e48]
          - generic [ref=e51]: New
        - button "Cart" [ref=e52] [cursor=pointer]:
          - img [ref=e54]
          - generic [ref=e58]: Cart
        - button "Categories" [ref=e59] [cursor=pointer]:
          - img [ref=e60]
          - generic [ref=e61]: Categories
      - generic [ref=e62]:
        - generic [ref=e63]:
          - generic [ref=e64]:
            - img [ref=e65]
            - heading "Categories" [level=2] [ref=e66]
          - button [ref=e67] [cursor=pointer]:
            - img [ref=e68]
        - generic [ref=e71]:
          - generic [ref=e73] [cursor=pointer]: All Products
          - generic [ref=e75] [cursor=pointer]:
            - generic [ref=e76]: delete
            - button [ref=e77]:
              - img [ref=e78]
          - generic [ref=e81] [cursor=pointer]:
            - generic [ref=e82]: delete
            - button [ref=e83]:
              - img [ref=e84]
          - generic [ref=e87] [cursor=pointer]:
            - generic [ref=e88]: 3PIECE
            - button [ref=e89]:
              - img [ref=e90]
          - generic [ref=e94] [cursor=pointer]: delete
          - generic [ref=e96] [cursor=pointer]:
            - generic [ref=e97]: SAREE
            - button [ref=e98]:
              - img [ref=e99]
          - generic [ref=e102] [cursor=pointer]:
            - generic [ref=e103]: 1 PIECE
            - button [ref=e104]:
              - img [ref=e105]
          - generic [ref=e108] [cursor=pointer]:
            - generic [ref=e109]: DESHIO FACTORY
            - button [ref=e110]:
              - img [ref=e111]
          - generic [ref=e114] [cursor=pointer]:
            - generic [ref=e115]: delete
            - button [ref=e116]:
              - img [ref=e117]
          - generic [ref=e120] [cursor=pointer]:
            - generic [ref=e121]: 2 PIECE
            - button [ref=e122]:
              - img [ref=e123]
          - generic [ref=e127] [cursor=pointer]: WINTER SPEACIAL
          - generic [ref=e129] [cursor=pointer]:
            - generic [ref=e130]: ORNA
            - button [ref=e131]:
              - img [ref=e132]
          - generic [ref=e135] [cursor=pointer]:
            - generic [ref=e136]: HOME DECOR
            - button [ref=e137]:
              - img [ref=e138]
          - generic [ref=e141] [cursor=pointer]:
            - generic [ref=e142]: JEWELLERY
            - button [ref=e143]:
              - img [ref=e144]
          - generic [ref=e147] [cursor=pointer]:
            - generic [ref=e148]: ACCESSOIES
            - button [ref=e149]:
              - img [ref=e150]
          - generic [ref=e153] [cursor=pointer]:
            - generic [ref=e154]: JAMDANI SAREE
            - button [ref=e155]:
              - img [ref=e156]
          - generic [ref=e159] [cursor=pointer]:
            - generic [ref=e160]: FOOD
            - button [ref=e161]:
              - img [ref=e162]
    - contentinfo [ref=e165]:
      - generic [ref=e166]:
        - generic [ref=e167]:
          - heading "Our Outlets" [level=2] [ref=e170]
          - generic [ref=e172]:
            - generic [ref=e173]:
              - img "Bashundhara City Complex" [ref=e175]
              - heading "Bashundhara City Complex" [level=3] [ref=e177]
            - generic [ref=e178]:
              - img "Mirpur 12 Outlet" [ref=e180]
              - heading "Mirpur 12 Outlet" [level=3] [ref=e182]
            - generic [ref=e183]:
              - img "Jamuna Future Park" [ref=e185]
              - heading "Jamuna Future Park" [level=3] [ref=e187]
        - generic [ref=e188]:
          - generic [ref=e189]:
            - link "Deshio" [ref=e190] [cursor=pointer]:
              - /url: /e-commerce
            - paragraph [ref=e191]: A complete lifestyle brand — footwear, clothing, watches, and bags curated for everyday confidence across Bangladesh.
            - paragraph [ref=e192]: Quick Info
            - navigation [ref=e193]:
              - link "About Us" [ref=e194] [cursor=pointer]:
                - /url: /e-commerce/about
              - link "Contact Us" [ref=e195] [cursor=pointer]:
                - /url: /e-commerce/contact
              - link "Track Your Order" [ref=e196] [cursor=pointer]:
                - /url: /e-commerce/track
              - link "All Categories" [ref=e197] [cursor=pointer]:
                - /url: /e-commerce/categories
              - link "New & Popular" [ref=e198] [cursor=pointer]:
                - /url: /e-commerce/products
            - generic [ref=e199]:
              - link "Facebook" [ref=e200] [cursor=pointer]:
                - /url: https://facebook.com/Deshio
                - img [ref=e201]
              - link "Instagram" [ref=e203] [cursor=pointer]:
                - /url: https://instagram.com/Deshio
                - img [ref=e204]
              - link "YouTube" [ref=e207] [cursor=pointer]:
                - /url: https://youtube.com/Deshio
                - img [ref=e208]
          - generic [ref=e211]:
            - paragraph [ref=e212]: Useful Links
            - navigation [ref=e213]:
              - link "New Arrivals" [ref=e214] [cursor=pointer]:
                - /url: /e-commerce/products
              - link "Collections" [ref=e215] [cursor=pointer]:
                - /url: /e-commerce/categories
              - link "My Account" [ref=e216] [cursor=pointer]:
                - /url: /e-commerce/my-account
              - link "My Orders" [ref=e217] [cursor=pointer]:
                - /url: /e-commerce/orders
              - link "Wishlist" [ref=e218] [cursor=pointer]:
                - /url: /e-commerce/wishlist
          - generic [ref=e219]:
            - paragraph [ref=e220]: Our Promise
            - generic [ref=e221]:
              - generic [ref=e222]:
                - paragraph [ref=e223]: Comfort & Quality Assured
                - paragraph [ref=e224]: Thoughtfully selected with quality finishing.
              - generic [ref=e225]:
                - paragraph [ref=e226]: In-Store & Online Support
                - paragraph [ref=e227]: Visit us or order easily — responsive service.
              - generic [ref=e228]:
                - paragraph [ref=e229]: Nationwide Delivery
                - paragraph [ref=e230]: Smooth and reliable delivery across Bangladesh.
            - 'link "International Orders WhatsApp: 01942565664" [ref=e231] [cursor=pointer]':
              - /url: https://wa.me/8801942565664
              - img [ref=e232]
              - generic [ref=e234]:
                - paragraph [ref=e235]: International Orders
                - paragraph [ref=e236]:
                  - text: "WhatsApp:"
                  - strong [ref=e237]: "01942565664"
        - generic [ref=e238]:
          - paragraph [ref=e239]: Our Store Locations
          - generic [ref=e240]:
            - generic [ref=e241]:
              - paragraph [ref=e242]: Mirpur 12
              - generic [ref=e243]:
                - img [ref=e244]
                - generic [ref=e247]: Level 3, Hazi Kujrat Ali Mollah Market, Mirpur 12
              - generic [ref=e248]:
                - img [ref=e249]
                - link "01942565664" [ref=e251] [cursor=pointer]:
                  - /url: tel:01942565664
            - generic [ref=e252]:
              - paragraph [ref=e253]: Jamuna Future Park
              - generic [ref=e254]:
                - img [ref=e255]
                - generic [ref=e258]: 3C-17A, Level 3, Jamuna Future Park
              - generic [ref=e259]:
                - img [ref=e260]
                - link "01307130535" [ref=e262] [cursor=pointer]:
                  - /url: tel:01307130535
            - generic [ref=e263]:
              - paragraph [ref=e264]: Bashundhara City
              - generic [ref=e265]:
                - img [ref=e266]
                - generic [ref=e269]: 38, 39, 40, Block D, Level 5, Bashundhara City
              - generic [ref=e270]:
                - img [ref=e271]
                - link "01336041064" [ref=e273] [cursor=pointer]:
                  - /url: tel:01336041064
        - generic [ref=e274]:
          - paragraph [ref=e275]: © 2026 Deshio STORE — Handcrafted for Confidence.
          - generic [ref=e276]:
            - generic [ref=e277]: bKash
            - generic [ref=e278]: Nagad
            - generic [ref=e279]: Visa
            - generic [ref=e280]: Mastercard
```

# Test source

```ts
  1  | // e2e/tests/01_startup.spec.ts
  2  | import { test, expect } from '../fixtures/app.fixture';
  3  | 
  4  | test.describe('App Startup', () => {
  5  |   test('fresh start shows empty sidebar and placeholder writing area', async ({ page }) => {
  6  |     await page.goto('/');
  7  | 
  8  |     const sidebar = page.locator('[data-testid="sidebar"]');
  9  |     await expect(sidebar).toBeVisible({
  10 |       timeout: 2000,
  11 |     });
  12 | 
  13 |     const flareonItems = page.locator('[data-testid="flareon-item"]');
  14 |     await expect(flareonItems).toHaveCount(0, {
  15 |       timeout: 2000,
  16 |     });
  17 | 
  18 |     const placeholder = page.locator('[data-testid="writing-area-placeholder"]');
  19 |     await expect(placeholder).toBeVisible();
  20 |     await expect(placeholder).toContainText('Select a Flareon');
  21 |   });
  22 | 
  23 |   test('writing area is not visible without a selected Flareon', async ({ page }) => {
  24 |     await page.goto('/');
  25 | 
  26 |     const textarea = page.locator('[data-testid="writing-textarea"]');
  27 |     await expect(textarea).not.toBeVisible();
  28 |   });
  29 | 
  30 |   test('app loads within 2 seconds', async ({ page }) => {
  31 |     const start = Date.now();
  32 |     await page.goto('/');
> 33 |     await page.locator('[data-testid="sidebar"]').waitFor({ state: 'visible' });
     |                                                   ^ Error: locator.waitFor: Test timeout of 30000ms exceeded.
  34 |     const elapsed = Date.now() - start;
  35 | 
  36 |     expect(elapsed).toBeLessThan(2000);
  37 |   }, {
  38 |     annotation: {
  39 |       type: 'performance',
  40 |       description: `[E2E Startup] App did not render within 2 seconds.
  41 |   This violates the core product performance requirement.
  42 |   Check: Is the backend responding? Is the Next.js build optimized?
  43 |   Run: curl http://localhost:8000/api/health to verify backend is up.`
  44 |     }
  45 |   });
  46 | });
  47 | 
```
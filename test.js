import puppeteer from 'puppeteer';

async function callProductDetails(spuId) {
  const page = await puppeteer.launch({ headless: true }).then(b => b.newPage());

  // 1) Navigate to any PopMart page that loads the signing logic
  await page.goto('https://www.popmart.com/us/pop-now/box/' + spuId, {
    waitUntil: 'networkidle0'
  });

  // 2) In the page context, find and call the internal sign() function
  //    (you’ll need to inspect DevTools to locate the real function name/namespace)
  //    Here we assume there's a global `window.__SIGN__` method that takes (path, bodyObj)
  const apiResponse = await page.evaluate(async (spuId) => {
    // Compose your request payload
    const payload = { spuId };

    // The path we want to sign
    const path = '/shop/v1/shop/productDetails';

    // t = current Unix seconds
    const t = Math.floor(Date.now() / 1000);

    // Call the site’s own sign() util to get the signature
    // (Replace __SIGN__ with the actual function you find in window)
    const s = window.__SIGN__(path, payload, t);

    // Now perform the fetch using the freshly computed s and t
    const query = new URLSearchParams({ spuId, s, t });
    const url = `https://prod-global-api.popmart.com${path}?${query}`;

    const resp = await fetch(url, {
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'ClientKey': window.__CLIENT_KEY__,      // mirror global clientKey
        'x-sign': `${s},${t}`,
        'User-Agent': navigator.userAgent,
        'Origin': location.origin,
        'Referer': location.origin + location.pathname,
      },
      credentials: 'include'
    });

    return resp.json();
  }, spuId);

  console.log('API response:', apiResponse);
  await page.browser().close();
}

callProductDetails(3013).catch(console.error);

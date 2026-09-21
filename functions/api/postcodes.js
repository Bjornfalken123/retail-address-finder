const UPSTREAM_URL = "https://gist.githubusercontent.com/Gronis/175de473918d9487946da07a1c4d3118/raw/zipcodes.json";

export async function onRequestGet() {
  try {
    const upstream = await fetch(UPSTREAM_URL, {
      headers: {
        "accept": "application/json",
        "user-agent": "retail-address-finder-postcode-map"
      },
      cf: {
        cacheEverything: true,
        cacheTtl: 86400
      }
    });

    if (!upstream.ok) {
      return json({ error: `Postcode source returned ${upstream.status}` }, 502);
    }

    const rows = await upstream.json();
    if (!Array.isArray(rows) || rows.length === 0) {
      return json({ error: "Postcode source returned no rows." }, 502);
    }

    return new Response(JSON.stringify(rows), {
      status: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=3600, s-maxage=86400"
      }
    });
  } catch (error) {
    return json({ error: error.message || "Could not load postcode data." }, 500);
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

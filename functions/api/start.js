export async function onRequestPost(context) {
  try {
    const body = await context.request.json();

    const exportMode = String(body.exportMode || "chain").trim();
    const chain = String(body.chain || "").trim();
    const country = String(body.country || "").trim();
    const category = String(body.category || "all").trim();
    const subtype = String(body.subtype || "auto").trim();
    const format = String(body.format || "CSV").trim();
    const source = String(body.source || "OpenStreetMap").trim();

    if (!country) {
      return json({ error: "Please enter a country." }, 400);
    }

    if (exportMode === "chain" && !chain) {
      return json({ error: "Please enter a chain or brand." }, 400);
    }

    if (!["chain", "category"].includes(exportMode)) {
      return json({ error: "Invalid export mode." }, 400);
    }

    const env = context.env;
    const owner = env.GITHUB_OWNER;
    const repo = env.GITHUB_REPO;
    const workflow = env.GITHUB_WORKFLOW_FILE || "export-custom.yml";
    const ref = env.GITHUB_REF || "main";
    const token = env.GITHUB_TOKEN;

    if (!owner || !repo || !token) {
      return json({
        error: "Cloudflare is missing GitHub settings. Check GITHUB_OWNER, GITHUB_REPO and GITHUB_TOKEN."
      }, 500);
    }

    const jobId = createJobId({
      exportMode,
      country,
      chain,
      category,
      subtype
    });

    const fileName = `${jobId}.csv`;

    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
      {
        method: "POST",
        headers: {
          "accept": "application/vnd.github+json",
          "authorization": `Bearer ${token}`,
          "content-type": "application/json",
          "user-agent": "retail-address-finder"
        },
        body: JSON.stringify({
          ref,
          inputs: {
            export_mode: exportMode,
            chain,
            country,
            category,
            subtype,
            format,
            source,
            job_id: jobId
          }
        })
      }
    );

    if (!response.ok) {
      const text = await response.text();
      return json({ error: `GitHub responded ${response.status}: ${text}` }, 500);
    }

    return json({
      ok: true,
      jobId,
      fileName,
      exportMode,
      chain,
      country,
      category,
      subtype,
      actionsUrl: `https://github.com/${owner}/${repo}/actions/workflows/${workflow}`
    });
  } catch (error) {
    return json({ error: error.message || "Unknown error." }, 500);
  }
}

function createJobId({ exportMode, country, chain, category, subtype }) {
  const raw =
    exportMode === "chain"
      ? `${country}_${chain || "chain"}_${category}_${subtype}`
      : `${country}_${category}_${subtype}`;

  const clean = raw
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

  const timestamp = new Date()
    .toISOString()
    .replace(/[-:.TZ]/g, "")
    .slice(0, 14);

  return `${timestamp}_${clean}`;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8"
    }
  });
}

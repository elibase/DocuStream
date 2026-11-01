# Build the invoice workflow in UiPath Studio Web

This guide is for the existing `uipath/RPA Workflow` project. Its configuration
uses Visual Basic expressions, cross-platform (`Portable`) compatibility,
UiPath.System.Activities 26.10.0, and UiPath.WebAPI.Activities 2.5.2.
`Main.xaml` currently contains a Sequence with a Manual Trigger. This guide does
not modify that workflow for you. Work through each checkpoint in Studio Web.

Use **Studio Web in your browser with Assistant/Robot on this computer**.
You do not need to install Studio Desktop. A cloud robot cannot
reach your computer's API at `127.0.0.1`. Start with the original fictional PDFs;
the varied layouts currently expose date-formatting problems that correctly
cause NeedsReview. No payment approval is part of this workflow.

See [the workflow diagram](UiPath_Workflow.md) while building.

## 1. Start the Python service

In the VS Code terminal, from the DocuStream repository root:

```powershell
ollama list
$env:EXTRACTION_BACKEND = "ollama"
.\.venv\Scripts\python.exe -m uvicorn src.routes:app --reload
```

Confirm that `qwen3:8b` appears in the model list. If Ollama is not running,
open a separate terminal and run `ollama serve`; leave it running. If the server
is already running, do not start a second copy.

Leave the API terminal open. Visit http://127.0.0.1:8000/docs and try `/health`.
You should receive HTTP 200 with `{"status":"ok"}`.

## 2. Connect Studio Web to your computer and open the project

1. Sign in to UiPath Automation Cloud in your browser and open **Studio**.
2. Open your existing solution and its **RPA Workflow** project, then `Main.xaml`.
   Use the RPA workflow designer, not a cloud-only API workflow project.
3. Follow the canvas's local-setup banner if present. Install the Windows
   **UiPath Robot/Assistant** using the installer offered there; this is different
   from installing the full Studio Desktop editor.
4. Open Assistant and sign in with the same user, organization, and tenant as
   Studio Web. Keep Assistant running. Use its current supported version; UiPath's
   local-setup guide specifies STS 2026.0.190/LTS 2025.10.15 or newer.
5. In Chrome/Edge, allow access to local apps/devices when prompted. Refresh
   Studio Web after Assistant connects if necessary.
6. Check the solution's Local Workspace location. Confirm the workflow you are
   editing corresponds to this repository's `uipath/RPA Workflow`, not an older
   `Solution/` copy or another downloaded workspace. A browser project is not
   automatically synchronized to whichever XAML is open in VS Code. If the local
   workspace is elsewhere, synchronize/export the finished project deliberately
   before committing; do not work on two copies independently.
7. Expand the menu beside **Debug** and select **On local machine**. Do not
   select **On cloud** for this walkthrough.
8. Wait for dependency restore. Use **+ Add activity** to search for activities.
   Existing dependencies include System and WebAPI. For CSV, search **Write CSV**;
   adding an available activity installs its package automatically. Studio Web
   does not expose Desktop's Manage Packages dialog. If Write CSV is absent,
   check the available categories and project compatibility; manual dependency
   management requires Studio Desktop, not an undiscovered Web menu.
   This is not a Python pip dependency. CSV activities do not require an Excel scope.

Sources: [local setup](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/local-setup-for-rpa-workflow-and-app-projects),
[local debugging](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/running-a-project),
[CSV package example](https://docs.uipath.com/activities/other/latest/productivity/filter-csv-files).

**Setup checkpoint:** Studio Web shows Assistant connected and local debugging is
available. If your organization's policy blocks local execution, resolve that
before proceeding. The local robot is what accesses the C: drive and localhost;
the browser is the editor. No public tunnel or paid model API is needed.

Your main sequence is the container where the steps run from top to bottom.
Keep the existing Manual Trigger first, and add activities below it using the
**+ Add activity** button. Rename activities with meaningful
Display Names, such as `Check API health`.

## 3. Understand expressions and variables

- A variable stores a value between activities.
- **Set Variable Value** sets a variable. Where this guide says Assign, use Set
  Variable Value in Studio Web: choose the named variable and enter the right-hand
  expression as Value. Some designers also expose an Assign activity.
- An **If** activity chooses Then or Else based on a Boolean expression.
- A **For Each** repeats its body for each item.
- **Try Catch** handles an exception without losing the rest of the batch.
- **Log Message** writes a message to Studio Web's **Run output** panel.

Expressions here are Visual Basic. Strings use double quotes, for example
`"http://127.0.0.1:8000"`. Enter expressions through the expression editor
(usually **+ → Open in Advanced Editor / Expression Editor**). A field in plain
text mode may not evaluate an expression. UI labels can vary slightly by Studio
build. Expand the selected activity's inputs and advanced options to configure it.

Open **Data Manager** from the left of the designer. Beside **Variables**, click
**Add new item (+)**, enter name/type/default, and select **Create**. Studio Web's
documented variables are global to the workflow. For types not listed, select
**Advanced types**. Activity outputs can create typed variables automatically;
select the output's variable/create option, then find the generated variable in
Data Manager. Do not rely on Desktop's Ctrl+K shortcut in the browser.
[Variable reference](https://docs.uipath.com/studio-web/automation-cloud/latest/user-guide/managing-the-data-in-a-project).

Create these variables first:

| Name | Type | Initial value / assignment |
| --- | --- | --- |
| `repoRoot` | String | `"C:\Users\Eliba\source\dev\active\DocuStream"` |
| `apiBaseUrl` | String | `"http://127.0.0.1:8000"` |
| `inputFolder` | String | Assign `System.IO.Path.Combine(repoRoot, "input", "invoices")` |
| `runId` | String | Assign `System.DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff") & "_" & System.Guid.NewGuid().ToString("N")` |
| `runFolder` | String | Assign `System.IO.Path.Combine(repoRoot, "output", "uipath", runId)` |
| `invoiceFiles` | String[] | Set during enumeration |
| `currentFile` | String | Used as the For Each item name later |
| `responseText` | String | `""` |
| `statusCode` | Int32 | `0` |
| `invoiceJson` | Newtonsoft.Json.Linq.JObject | Leave unset |
| `results` | System.Data.DataTable | Created later |

The absolute `repoRoot` is intentional for your first local run: the UiPath
working directory may differ from the repository root. Later expose it as an
input argument/configuration value. Do not derive it from an unverified working
directory and do not change machine-global environment variables.

Add **Create Folder** activities for `inputFolder` and `runFolder`. Use each
variable as the folder path. Unique run folders preserve previous CSV reports.

## 4. First checkpoint: call GET /health

Use the WebAPI package's **HTTP Request**, class
`UiPath.Web.Activities.Http.NetHttpClient`. Do not choose the Integration Service
connector, Orchestrator HTTP Request, or HTTP Request (legacy).

Set method **GET**, URL `apiBaseUrl & "/health"`, body **None**, authentication
**No authentication**, timeout **10000** milliseconds, and retry **No retry**.
Set Continue on error **False**. In its **Response content** output, create
`healthResponse` using the output's create/save-variable control so Studio supplies the response type. Do not make it
a String. Read `CInt(healthResponse.StatusCode)` and `healthResponse.TextContent`.
These properties belong to the modern response object, not separate legacy outputs.
[Official HTTP Request reference](https://docs.uipath.com/activities/other/latest/developer/http-request).

1. Add **If** after the request, condition `CInt(healthResponse.StatusCode) <> 200`.
2. In Then, add **Throw**, exception:
   `New System.Exception("FastAPI health check failed. Start the Python API.")`.
3. After the If, add **Log Message**, message `"API health check passed"`.
4. Wait for edits to save, open the menu next to **Debug**, choose **On local
   machine**, and run. Open **Run output**. Use **Debug step-by-step** if you
   want to inspect one activity at a time.

**Checkpoint:** see the health message and a `GET /health` request in the Python
terminal. A connection exception means the API is unavailable; fix it before
building the loop. Health does not check that Ollama is ready.

## 5. Second checkpoint: upload one PDF

Temporarily add an Assign:

```vb
currentFile = System.IO.Path.Combine(repoRoot, "sample_data", "invoices", "invoice_001.pdf")
```

Add another modern **HTTP Request**, named `Extract current invoice`.
If the activity's advanced configuration exposes **cURL Command Text**, paste the
following there and select **cURL import**. The WebAPI activity supports this,
but its visibility can differ in the Studio Web designer. If those controls are
not exposed, use the manual multipart configuration below instead:

```text
curl -X POST http://127.0.0.1:8000/extract -F "file=@C:/Users/Eliba/source/dev/active/DocuStream/sample_data/invoices/invoice_001.pdf;type=application/pdf"
```

Confirm POST and multipart body, and that the file part's name is **file**.
Inspect the generated file-part expression and replace **only its path value**
with the expression `currentFile`. Retain the part name `"file"` and MIME type
`"application/pdf"`. Do not send a JSON object containing a file path. Do not
manually set the multipart Content-Type header: the activity supplies its boundary.

For manual configuration, select method POST, request body type **Multipart form
data**, then open **Form data parts** in the expression/advanced editor. Do not
use an Integration Service connector's JSON-body editor. The constructor is
`New FileFormDataPart(currentFile, "file", "application/pdf")` inside a
`List(Of FormDataPart)`, for example:

```vb
New System.Collections.Generic.List(Of FormDataPart) From {
    New FileFormDataPart(currentFile, "file", "application/pdf")
}
```

Resolve these types using the expression editor's imports/type autocomplete
from the WebAPI package. When exposed, cURL import avoids guessing their
namespace. Do not use the plain local-files list unless its generated part name
is confirmed to be `file`. See the HTTP Request reference linked above.

Set URL to `apiBaseUrl & "/extract"`, timeout **180000** milliseconds, no
authentication, no retry, Continue on error False. Leave save-response-as-file
off. Save Response content to a typed output variable `extractResponse` using
the output variable control. Add Set Variable Value activities for these assignments:

```vb
statusCode = CInt(extractResponse.StatusCode)
responseText = extractResponse.TextContent
```

Add **Log Message** with `"HTTP " & statusCode.ToString() & ": " & responseText`
for this fictional one-file test. Later log statuses/reasons rather than full
invoice contents. Run locally and check the API terminal for POST /extract.

**Checkpoint:** HTTP 200, invoice number DEMO-2026-001, total 277.42, and
validation_status ReadyForReview. The first request may be slower while Qwen loads.
If the activity throws for a non-200 response, handle it in Try Catch as described
below; do not deserialize an error body as an invoice.

## 6. Read the JSON response

After a successful POST, add an **If** with condition `statusCode = 200`.
Inside Then, add **Deserialize JSON** from WebAPI:

- Input JSON string: `responseText`.
- Output JSON object: `invoiceJson` (JObject).

Then Log Message:

```vb
System.Convert.ToString(invoiceJson("source_file")) & " -> " & System.Convert.ToString(invoiceJson("validation_status"))
```

Read optional values with `System.Convert.ToString(invoiceJson("due_date"))`;
do not parse dates or money again in UiPath. The API owns these checks. A successful
response includes exception_reasons as an array, not a plain text message.

## 7. Build the batch results table

Before the file loop, add **Build Data Table**. Open its table editor, remove the
default sample columns/rows, and create these columns **in this order**, all String:

```text
source_file
invoice_number
vendor_name
invoice_date
due_date
currency
subtotal
tax
total
extraction_status
validation_status
exception_reasons
processed_at
source_path
retryable
```

Store the output in `results`. `source_path` and `retryable` are local workflow
columns, not fields returned by FastAPI. Do not put sample rows in the table.

## 8. Replace the one-file assignment with a loop

1. Copy just `invoice_001.pdf` into `input/invoices/` using File Explorer. Keep
   the sample originals in `sample_data/` untouched.
2. Remove the temporary `currentFile` assignment from section 5.
3. Before the loop, Assign:

   ```vb
   invoiceFiles = System.IO.Directory.GetFiles(inputFolder).Where(Function(p) System.IO.Path.GetExtension(p).Equals(".pdf", System.StringComparison.OrdinalIgnoreCase)).OrderBy(Function(p) p).ToArray()
   ```

   Import `System.Linq` if Studio flags Where/OrderBy. Only top-level PDFs are
   included; log unsupported files separately if you later broaden enumeration.
4. Add **If** `invoiceFiles.Length = 0`: Then log `"No PDFs to process"`;
   Else place the remaining batch workflow below inside that Else sequence.
5. Add **For Each**, collection `invoiceFiles`, item name `currentFile`, type
   argument String. This generic For Each uses file paths, not file-resource objects.
6. Move the POST request and JSON handling into its body. Do not repeat GET /health
   for every file and do not run uploads in parallel for this first version.
7. Wrap each iteration's request/parse/record steps in **Try Catch**. Add a catch
   for System.Exception, variable `ex`.
8. Reset `statusCode = 0`, `responseText = ""`, and `invoiceJson = Nothing`
   at the beginning of each iteration so an error cannot reuse the prior result.

Inside the HTTP-200 Then branch, after Deserialize JSON, add **Add Data Row**.
DataTable: `results`. ArrayRow expression:

```vb
New Object() {
    System.IO.Path.GetFileName(currentFile),
    System.Convert.ToString(invoiceJson("invoice_number")),
    System.Convert.ToString(invoiceJson("vendor_name")),
    System.Convert.ToString(invoiceJson("invoice_date")),
    System.Convert.ToString(invoiceJson("due_date")),
    System.Convert.ToString(invoiceJson("currency")),
    System.Convert.ToString(invoiceJson("subtotal")),
    System.Convert.ToString(invoiceJson("tax")),
    System.Convert.ToString(invoiceJson("total")),
    System.Convert.ToString(invoiceJson("extraction_status")),
    System.Convert.ToString(invoiceJson("validation_status")),
    invoiceJson("exception_reasons").ToString(Newtonsoft.Json.Formatting.None),
    System.Convert.ToString(invoiceJson("processed_at")),
    currentFile,
    "False"
}
```

## 9. Record errors without losing the batch

In the non-200 Else branch, add Add Data Row using this ArrayRow:

```vb
New Object() {
    System.IO.Path.GetFileName(currentFile), "", "", "", "", "", "", "", "",
    "Failed", "Failed",
    Newtonsoft.Json.JsonConvert.SerializeObject(New String() {"HTTP " & statusCode.ToString() & ": " & responseText}),
    System.DateTime.UtcNow.ToString("o"), currentFile,
    If(statusCode = 502 OrElse statusCode = 503 OrElse statusCode = 504 OrElse statusCode >= 500, "True", "False")
}
```

In Catch System.Exception, Log Message at Error level with the filename and
`ex.GetType().Name`, then add a row with:

```vb
New Object() {
    System.IO.Path.GetFileName(currentFile), "", "", "", "", "", "", "", "",
    "Failed", "Failed",
    Newtonsoft.Json.JsonConvert.SerializeObject(New String() {"Request or response processing failed: " & ex.GetType().Name}),
    System.DateTime.UtcNow.ToString("o"), currentFile, "True"
}
```

Keep network exceptions retryable. If the HTTP activity throws before exposing
an error status, the catch conservatively leaves the file for manual retry.
Do not automatically retry during initial development; first identify the cause.

| Response | Meaning / action |
| --- | --- |
| 200 + ReadyForReview | Record fields; ready folder after CSV save |
| 200 + NeedsReview | Record fields/reasons; review folder after CSV save |
| 413, 415, 422 | Document/request problem; failed folder after CSV save |
| 502, 503, 504 or other server error | Keep input for retry; record failure |
| Connection/timeout/JSON exception | Keep input; record exception type |

Missing-field or invalid-date invoices usually return **200 NeedsReview**, not
an HTTP error. On this API 422 can mean malformed upload or unreadable PDF.

## 10. Flag duplicates before routing

After the upload loop, use **+ Add activity** to add **Invoke Code**, Language VB.
Expand its Code editor and Arguments collection. This is a small local
data-table step, not another model call. In Arguments add `dt`, direction
In/Out, type System.Data.DataTable, value `results`. Paste:

```vb
Dim groups As New System.Collections.Generic.Dictionary(Of String, System.Collections.Generic.List(Of System.Data.DataRow))
For Each row As System.Data.DataRow In dt.Rows
    If row("extraction_status").ToString() <> "Processed" Then Continue For
    Dim vendor = System.Text.RegularExpressions.Regex.Replace(row("vendor_name").ToString().Trim(), "\s+", " ").ToLowerInvariant()
    Dim number = System.Text.RegularExpressions.Regex.Replace(row("invoice_number").ToString().Trim(), "\s+", " ").ToLowerInvariant()
    If vendor = "" OrElse number = "" Then Continue For
    Dim key = Newtonsoft.Json.JsonConvert.SerializeObject(New String() {vendor, number})
    If Not groups.ContainsKey(key) Then groups(key) = New System.Collections.Generic.List(Of System.Data.DataRow)
    groups(key).Add(row)
Next
For Each group In groups.Values
    If group.Count < 2 Then Continue For
    For Each row In group
        Dim reasons = Newtonsoft.Json.Linq.JArray.Parse(row("exception_reasons").ToString())
        reasons.Add("Duplicate invoice: vendor and invoice number repeat in this batch")
        row("exception_reasons") = reasons.ToString(Newtonsoft.Json.Formatting.None)
        row("validation_status") = "NeedsReview"
    Next
Next
```

This marks every copy, including the first. It is batch duplicate detection,
not historical lookup. Cross-language Unicode case conversion may differ from
Python's casefold for some non-ASCII text; the current fictional names are ASCII.

## 11. Save CSV before moving anything

After duplicate checks, add **Write CSV** from the installed Excel package.
Source DataTable: `results`. File path:

```vb
System.IO.Path.Combine(runFolder, "results.csv")
```

Include column names/headers: True. Delimiter: comma. Encoding: UTF-8. Use write/
replace mode, not append, for this unique run report. No Excel scope is needed.

Run now with one file and inspect the CSV: one header and one invoice row, reasons
stored as JSON. If saving fails, stop and leave inputs untouched. Add a Log Message
that records the report path. Do not use the Python `src/main.py` CSV generator
as a substitute: that command bypasses the model.

## 12. Route recorded files

After Write CSV, add **For Each Row in Data Table**, input `results`, item `row`.
Create String variables `destinationFolder` and `destinationPath` at main scope.

1. Add If `row("retryable").ToString() = "True"`.
   Then log `"Left in input for retry: " & row("source_file").ToString()`.
2. In Else, Assign:

   ```vb
   destinationFolder = System.IO.Path.Combine(runFolder, If(row("validation_status").ToString() = "ReadyForReview", "ready_for_review", If(row("validation_status").ToString() = "NeedsReview", "needs_review", "failed")))
   ```

3. Create Folder at `destinationFolder`.
4. Assign `destinationPath = System.IO.Path.Combine(destinationFolder, row("source_file").ToString())`.
5. Inside a separate Try Catch, add **Move File** from `row("source_path").ToString()`
   to `destinationPath`. Overwrite/replace existing: False.
6. After a successful move, log the filename, validation status, and destination.
7. On a move exception, log Error and leave the source available. Do not change
   a successful extraction to Failed solely because a move failed: record routing
   failure separately.

For a durable routing log, use **Append Line** (or Append Text) at
`System.IO.Path.Combine(runFolder, "routing.log")`. Append a UTC timestamp,
filename, action (`Moved`, `LeftForRetry`, `MoveFailed`), and status after each
action. Do not record PDF text. Test this log path before moving the first file.

Run folders plus no-overwrite moves prevent destination collisions. Under a
normal complete run, moved files are no longer enumerated on the next run.

**Important limit:** this first workflow is not crash-safe exactly-once processing.
A crash after CSV save but before moving a file leaves it in input, so the next run
can record it again. Before checking off milestone 4's repeat-run requirement,
add a durable per-file identity/result ledger and resume pending moves. A ledger
should distinguish extracted, result-saved, and moved states, preserve business
duplicates for review, and use file content hashes for exact-file repeat checks.
Do not claim full idempotency from folder movement alone.

## 13. Test in this order

1. One original invoice: HTTP 200, expected values, one CSV row, correct move.
2. Three original invoices: three rows and three destinations; no stale responses.
3. Two differently named copies of one invoice: both rows NeedsReview after
   duplicate checks, not just the second.
4. One varied invoice: inspect returned dates and NeedsReview reasons. Do not
   assume all varied PDFs should pass validation with the current model.
5. A text file renamed `.pdf`: a failure row; later valid PDFs still process.
6. Stop Ollama while FastAPI stays up: health may pass, extraction fails; inputs
   remain available for retry. Restart Ollama afterwards.
7. Stop FastAPI: health check stops the run before processing files.
8. Run again after normal successful routing: moved PDFs do not process again.
9. Deliberately test a saved-result/pending-move restart before calling the full
   milestone complete; this needs the ledger extension described above.

Use copies of synthetic PDFs for all tests. Inspect Studio Output, Python server
requests, results.csv, routing.log, and the run's destination folders together.
Studio's Log Message output alone is not a durable audit file.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| HTTP activity asks for a connector connection | Wrong HTTP Request activity; choose WebAPI's modern activity |
| FastAPI says field `file` is missing | Multipart part name must be file; path strings alone are not uploads |
| String/type conversion errors on response | Save the typed activity output using its variable control; access TextContent separately |
| Cannot resolve JObject | Browse for Newtonsoft.Json.Linq.JObject in the variable type selector |
| Cannot resolve FormDataPart | Use cURL import and inspect its generated expression/type imports |
| Nothing reaches the Python terminal | Check local execution, URL, and whether POST is inside the loop |
| Request fails near ten seconds | Set extraction request timeout to 180000 ms, not the default |
| CSV activity absent | Search + Add activity; packages install automatically. Manual dependency management is a Desktop feature |
| Results disappear on another run | Use runFolder/results.csv, not a single overwritten global CSV |

These instructions are based on your project files and current UiPath activity
documentation. They have not been executed in your Studio Web session. Validate
each checkpoint using On local machine; exact control labels can vary with
Studio Web rollouts. Activity availability and advanced editors may differ by tenant.

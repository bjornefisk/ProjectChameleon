# Project Chameleon presentation

Short presentation outline for a five-minute review. Use one slide per section. Keep the spoken explanation plain and show the actual output during the demo.

## Slide 1: The problem

**Title:** Resize without losing the design

**Show:** A source design and its target canvas.

**Say:**

Project Chameleon moves a design to a new canvas. The challenge is keeping every part of the source while making the new layout fit.

## Slide 2: What must stay

**Title:** Preserve the source

**Show:** A short list beside the source design.

**Say:**

The program keeps every item, identifier, count, order, type, text, image, and source link. It does not redraw images or rewrite text.

## Slide 3: What may change

**Title:** Change only layout values

**Show:** The same items on the target canvas.

**Say:**

Only four things may change: target canvas size, item position, item size, and text size. Changed numbers must be finite whole numbers.

## Slide 4: How it chooses a layout

**Title:** Try, measure, keep

**Show:** Four small layout drafts, then one selected result.

**Say:**

The program tries four approved layout patterns. Each draft is drawn and measured. A draft stays only when it passes every required check. The program then picks the best passing draft with the same result on every run.

**Plain definitions:**

- A draft is one possible arrangement.
- The drawing tool renders the design for measurement.
- A required check is a rule that the final file must pass.

## Slide 5: Safe failure

**Title:** No partial output

**Show:** A failed input and an empty output folder.

**Say:**

If no draft passes, the program reports a named failure and writes no design output. It does not hide an item, remove an image, or publish a partial result.

## Slide 6: Evidence

**Title:** What we have checked

**Show:** The recorded evidence list.

**Say:**

Gate 1 is complete. The drawing tool and rule checker passed their required local checks. The public Level 3 case, `1080x1350 -> 728x90`, produced a valid JSON and PNG pair in repeated local runs. The required native `x86_64` run `39711973748` passed. Locked package work also passed native run `40233682826`. Issue #81 covered 18 local synthetic cases.

## Slide 7: Honest limits

**Title:** What remains open

**Show:** Two columns: checked and not checked.

**Say:**

We do not claim an official organizer score, cross-platform matching, tests on hidden organizer examples, or release checks. Those checks need organizer or release evidence. Partner review was waived by the repository owner, and no partner approval is recorded.

## Slide 8: Demo and close

**Title:** Run the same path every time

**Show:** The input, command, JSON output, and PNG preview.

**Say:**

We run the offline command, inspect the JSON, inspect the preview, and report each result. The final package includes the source, the output, the evidence, and the open-check list.

## Demo commands

Run from a native `linux/amd64` environment:

```bash
cd chameleon
python -m engine.main
python -m unittest discover -s tests -p 'test_*.py' -v
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

## Presenter notes

- Use the actual public Level 3 input and output when available.
- Say “local evidence” when evidence came from this checkout.
- Do not call a check complete without a recorded result.
- Do not claim the project PDF is attached until the original file arrives.

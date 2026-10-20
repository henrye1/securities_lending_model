// Run with: node --test src/lib/model.test.ts  (Node >= 23 strips types natively)
import { test } from "node:test";
import assert from "node:assert/strict";
import { emptyStock, identity, removeStockAt, zeros } from "./model.ts";

test("removeStockAt drops the stock and its row/column in every matrix", () => {
  const stocks = [emptyStock(), emptyStock(), emptyStock()];
  stocks[0].name = "A"; stocks[1].name = "B"; stocks[2].name = "C";
  const eq = identity();
  eq[0][1] = eq[1][0] = 0.5;   // A-B
  eq[0][2] = eq[2][0] = 0.25;  // A-C
  eq[1][2] = eq[2][1] = 0.75;  // B-C
  const fxeq = zeros();
  fxeq[0][2] = 0.4;            // pair 1 x stock C
  const next = removeStockAt(
    { stocks, equity_correlation: eq, currency_correlation: identity(), currency_equity_correlation: fxeq },
    1,
  );
  assert.deepEqual(next.stocks.map((s) => s.name), ["A", "C"]);
  assert.equal(next.equity_correlation.length, 10);
  assert.equal(next.equity_correlation[0][1], 0.25); // A-C now sits at (0,1)
  assert.equal(next.equity_correlation[1][0], 0.25);
  assert.equal(next.equity_correlation[1][1], 1);
  assert.equal(next.equity_correlation[9][9], 1);    // padded back to identity
  assert.equal(next.currency_equity_correlation[0][1], 0.4); // stock column re-indexed
  assert.equal(next.currency_correlation[1][1], 1);
});

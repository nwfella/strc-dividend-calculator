/* STRC scenario engine — pure functions, no DOM. window.STRC_ENGINE. */
(function () {
  "use strict";

  // Linear interpolation: value at month m of `months` total.
  function lerp(start, end, months, m) {
    return start + (end - start) * (m / Math.max(1, months));
  }

  // One scenario run. cfg: {label, prob, priceNow, priceEnd, divStart, divEnd,
  //                         shares, costBasis, horizon, reinvest}
  function scenario(cfg) {
    const months = Math.max(1, Math.round(cfg.horizon));
    const cost = cfg.shares * cfg.costBasis;
    let shares = cfg.shares;
    let divIncome = 0;
    let price = cfg.priceNow;
    for (let m = 1; m <= months; m++) {
      price = lerp(cfg.priceNow, cfg.priceEnd, months, m);
      const divPerShare = lerp(cfg.divStart, cfg.divEnd, months, m);
      const divAmt = shares * divPerShare;
      if (cfg.reinvest) {
        shares += divAmt / price;
      }
      divIncome += divAmt;
    }
    const endPrice = cfg.priceEnd;
    const pricePnL = (endPrice - cfg.priceNow) * cfg.shares;
    const endValue = shares * endPrice;
    const totalReturn = endValue - cost + divIncome;
    const annDiv = ((cfg.divStart + cfg.divEnd) / 2) * 12;
    const avgDivPerShare = (cfg.divStart + cfg.divEnd) / 2;
    return {
      label: cfg.label,
      prob: cfg.prob,
      endPrice: round2(endPrice),
      pricePnL: round2(pricePnL),
      divIncome: round2(divIncome),
      endValue: round2(endValue),
      totalReturn: round2(totalReturn),
      priceRet: pricePnL / (cfg.priceNow * cfg.shares),
      totalRet: totalReturn / cost,
      yieldOnCost: annDiv / cfg.costBasis,
      curYield: annDiv / endPrice,
      breakevenMonths: cfg.reinvest
        ? null
        : Math.ceil(cost / (cfg.shares * avgDivPerShare)),
      endShares: round4(shares),
    };
  }

  // Run all scenarios + probability-weighted EV row.
  function evaluate(scenarios, base) {
    const rows = scenarios.map(function (s) {
      return scenario({
        label: s.label,
        prob: s.prob,
        priceNow: base.priceNow,
        priceEnd: s.priceEnd,
        divStart: s.divStart,
        divEnd: s.divEnd,
        shares: base.shares,
        costBasis: base.costBasis,
        horizon: base.horizon,
        reinvest: base.reinvest,
      });
    });
    const ev = {
      label: "EV (weighted)",
      prob: rows.reduce(function (a, r) { return a + r.prob; }, 0),
      endPrice: round2(rows.reduce(function (a, r) { return a + r.prob * r.endPrice; }, 0)),
      pricePnL: round2(rows.reduce(function (a, r) { return a + r.prob * r.pricePnL; }, 0)),
      divIncome: round2(rows.reduce(function (a, r) { return a + r.prob * r.divIncome; }, 0)),
      endValue: round2(rows.reduce(function (a, r) { return a + r.prob * r.endValue; }, 0)),
      totalReturn: round2(rows.reduce(function (a, r) { return a + r.prob * r.totalReturn; }, 0)),
      priceRet: rows.reduce(function (a, r) { return a + r.prob * r.priceRet; }, 0),
      totalRet: rows.reduce(function (a, r) { return a + r.prob * r.totalRet; }, 0),
      yieldOnCost: rows.reduce(function (a, r) { return a + r.prob * r.yieldOnCost; }, 0),
      curYield: rows.reduce(function (a, r) { return a + r.prob * r.curYield; }, 0),
      breakevenMonths: null,
      endShares: round4(rows.reduce(function (a, r) { return a + r.prob * r.endShares; }, 0)),
    };
    return rows.concat([ev]);
  }

  function round2(x) { return Math.round(x * 100) / 100; }
  function round4(x) { return Math.round(x * 10000) / 10000; }

  // Default scenario configs, anchored to live data (2026-08-06).
  function defaults(basePrice) {
    return [
      { label: "Bearish", prob: 0.30, priceEnd: 84.00, divStart: 1.00, divEnd: 0.80 },
      { label: "Neutral", prob: 0.40, priceEnd: basePrice, divStart: 1.00, divEnd: 1.00 },
      { label: "Bullish", prob: 0.30, priceEnd: 104.00, divStart: 1.00, divEnd: 1.10 },
    ];
  }

  var root = typeof window !== "undefined" ? window : globalThis;
  root.STRC_ENGINE = { scenario: scenario, evaluate: evaluate, defaults: defaults };
})();

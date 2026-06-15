import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import React from "react";

import { CodeBlock, copyStatusLabel } from "@/components/chat/CodeBlock";
import { MessageMarkdown, safeMarkdownHref } from "@/components/chat/MessageMarkdown";

void test("assistant markdown renders GFM tables, task lists, and fenced code blocks", () => {
  const content = [
    "| Control | Status |",
    "| --- | --- |",
    "| HTML | inert |",
    "",
    "- [x] Escape raw HTML",
    "",
    "```ts",
    "const value = 1;",
    "```",
  ].join("\n");

  const html = renderToStaticMarkup(React.createElement(MessageMarkdown, { content }));

  assert.match(html, /<table>/);
  assert.match(html, /<th>Control<\/th>/);
  assert.match(html, /type="checkbox"/);
  assert.match(html, /checked=""/);
  assert.match(html, /Copy code/);
  assert.match(html, /const[\s\S]*value[\s\S]*=[\s\S]*1[\s\S]*;/);
  assert.match(html, /TS/);
});

void test("assistant markdown escapes raw HTML and never emits executable attributes", () => {
  const content = [
    '<img src=x onerror="alert(1)">',
    '<script>alert("xss")</script>',
    "**Still markdown**",
  ].join("\n");

  const html = renderToStaticMarkup(React.createElement(MessageMarkdown, { content }));

  assert.doesNotMatch(html, /<img/i);
  assert.doesNotMatch(html, /<script/i);
  assert.doesNotMatch(html, /<[^>]+onerror=/i);
  assert.match(html, /&lt;img/);
  assert.match(html, /<strong>Still markdown<\/strong>/);
});

void test("assistant markdown only makes http, https, and mailto links clickable", () => {
  const content = [
    "[https](https://example.test/path)",
    "[http](http://example.test/path)",
    "[mail](mailto:support@example.test)",
    "[javascript](javascript:alert(1))",
    "[data](data:text/html,evil)",
    "[relative](/internal)",
  ].join(" ");

  const html = renderToStaticMarkup(React.createElement(MessageMarkdown, { content }));

  assert.equal(safeMarkdownHref("https://example.test/path"), "https://example.test/path");
  assert.equal(safeMarkdownHref("http://example.test/path"), "http://example.test/path");
  assert.equal(safeMarkdownHref("mailto:support@example.test"), "mailto:support@example.test");
  assert.equal(safeMarkdownHref("javascript:alert(1)"), undefined);
  assert.equal(safeMarkdownHref("data:text/html,evil"), undefined);
  assert.equal(safeMarkdownHref("/internal"), undefined);
  assert.match(html, /href="https:\/\/example.test\/path"/);
  assert.match(html, /href="http:\/\/example.test\/path"/);
  assert.match(html, /href="mailto:support@example.test"/);
  assert.match(html, /target="_blank"/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.doesNotMatch(html, /href="javascript:/i);
  assert.doesNotMatch(html, /href="data:/i);
  assert.doesNotMatch(html, /href="\/internal"/i);
});

void test("code blocks expose inert copy UI without evaluating code", () => {
  const source = 'throw new Error("must not run");';
  const html = renderToStaticMarkup(
    React.createElement(CodeBlock, {
      code: source,
      language: "python",
    }),
  );

  assert.match(html, /Copy code/);
  assert.equal(copyStatusLabel(false), "Copy code");
  assert.equal(copyStatusLabel(true), "Copied!");
  assert.match(html, /throw new Error/);
  assert.doesNotMatch(html, /dangerouslySetInnerHTML/);
});

void test("markdown renderer source does not bypass React escaping", () => {
  const source = readFileSync("components/chat/MessageMarkdown.tsx", "utf-8");

  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
  assert.doesNotMatch(source, /rehype-raw/);
});

void test("code block styling preserves preformatted source", () => {
  const componentSource = readFileSync("components/chat/CodeBlock.tsx", "utf-8");
  const globalCss = readFileSync("app/globals.css", "utf-8");

  assert.match(componentSource, /wrapLongLines=\{false\}/);
  assert.match(globalCss, /\.code-block \*/);
  assert.match(globalCss, /word-break:\s*normal/);
  assert.match(globalCss, /white-space:\s*pre/);
});

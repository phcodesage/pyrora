(() => {
  "use strict";

  const escapeHtml = (value) => value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character]));

  const paint = (source, expression, classify) => {
    let cursor = 0;
    let output = "";
    let match;

    while ((match = expression.exec(source)) !== null) {
      output += escapeHtml(source.slice(cursor, match.index));
      output += `<span class="${classify(match)}">${escapeHtml(match[0])}</span>`;
      cursor = match.index + match[0].length;
    }

    return output + escapeHtml(source.slice(cursor));
  };

  const highlightPython = (source) => paint(
    source,
    /(?<comment>#.*$)|(?<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(?<decorator>@[A-Za-z_][\w.]*)|(?<keyword>\b(?:from|import|as|async|await|class|def|return|while|for|in|if|else|pass)\b)|(?<constant>\b(?:True|False|None)\b)|(?<number>\b\d+(?:\.\d+)?\b)/gm,
    (match) => Object.keys(match.groups).find((name) => match.groups[name] !== undefined).replace("", "token-"),
  );

  const highlightShell = (source) => paint(
    source,
    /(?<comment>#.*$)|(?<string>"(?:\\.|[^"\\])*")|(?<command>\b(?:pip|pyrora|cd)\b)|(?<flag>--?[\w-]+)|(?<package>\[[^\]]+\])/gm,
    (match) => Object.keys(match.groups).find((name) => match.groups[name] !== undefined).replace("", "token-"),
  );

  document.querySelectorAll("pre code").forEach((block) => {
    const source = block.textContent;
    const shell = source.split("\n").every((line) => /^(?:pip |pyrora |cd |$)/.test(line));
    block.classList.add(shell ? "language-shell" : "language-python");
    block.innerHTML = shell ? highlightShell(source) : highlightPython(source);
  });
})();

// Static SVG geometry of the lucide icons the public pages draw (lucide-react 1.71.0, ISC licence),
// copied from the same icons as shell/icons/moduleIcons.ts and evidenceIcons.ts.
//
// Why a copy: lucide-react 1.x icons are Client Components ("use client" in Icon.mjs). Rendering them
// from these Server Component pages created client references that made Turbopack split the shared
// layout chunk, and every route (including /app, at its budget ceiling) paid about 0.3 KB more.
// Plain SVG from the server costs no JS. tests/public_site.test.ts checks this file against lucide.
export type IconNode = ReadonlyArray<readonly [string, Readonly<Record<string, string>>]>;

export const PUBLIC_ICON_NODES = {
  "kadi": [
    [
      "path",
      {
        "d": "M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"
      }
    ],
    [
      "path",
      {
        "d": "M14 2v5a1 1 0 0 0 1 1h5"
      }
    ],
    [
      "path",
      {
        "d": "M10 9H8"
      }
    ],
    [
      "path",
      {
        "d": "M16 13H8"
      }
    ],
    [
      "path",
      {
        "d": "M16 17H8"
      }
    ]
  ],
  "billnyay": [
    [
      "path",
      {
        "d": "M13 16H8"
      }
    ],
    [
      "path",
      {
        "d": "M14 8H8"
      }
    ],
    [
      "path",
      {
        "d": "M16 12H8"
      }
    ],
    [
      "path",
      {
        "d": "M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z"
      }
    ]
  ],
  "daavisetu": [
    [
      "rect",
      {
        "width": "8",
        "height": "4",
        "x": "8",
        "y": "2",
        "rx": "1",
        "ry": "1"
      }
    ],
    [
      "path",
      {
        "d": "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"
      }
    ],
    [
      "path",
      {
        "d": "m9 14 2 2 4-4"
      }
    ]
  ],
  "bimanyay": [
    [
      "path",
      {
        "d": "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"
      }
    ],
    [
      "path",
      {
        "d": "m9 12 2 2 4-4"
      }
    ]
  ],
  "schemesetu": [
    [
      "path",
      {
        "d": "M10 18v-7"
      }
    ],
    [
      "path",
      {
        "d": "M11.119 2.205a2 2 0 0 1 1.762 0l7.84 3.846A.5.5 0 0 1 20.5 7h-17a.5.5 0 0 1-.22-.949z"
      }
    ],
    [
      "path",
      {
        "d": "M14 18v-7"
      }
    ],
    [
      "path",
      {
        "d": "M18 18v-7"
      }
    ],
    [
      "path",
      {
        "d": "M3 22h18"
      }
    ],
    [
      "path",
      {
        "d": "M6 18v-7"
      }
    ]
  ],
  "dawacheck": [
    [
      "path",
      {
        "d": "m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"
      }
    ],
    [
      "path",
      {
        "d": "m8.5 8.5 7 7"
      }
    ]
  ],
  "verified": [
    [
      "path",
      {
        "d": "M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"
      }
    ],
    [
      "path",
      {
        "d": "m16 9-5.5 5.5L8 12"
      }
    ]
  ],
  "provisional": [
    [
      "path",
      {
        "d": "M5 22h14"
      }
    ],
    [
      "path",
      {
        "d": "M5 2h14"
      }
    ],
    [
      "path",
      {
        "d": "M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"
      }
    ],
    [
      "path",
      {
        "d": "M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"
      }
    ]
  ],
  "unevaluated": [
    [
      "path",
      {
        "d": "M10.1 2.182a10 10 0 0 1 3.8 0"
      }
    ],
    [
      "path",
      {
        "d": "M13.9 21.818a10 10 0 0 1-3.8 0"
      }
    ],
    [
      "path",
      {
        "d": "M17.609 3.721a10 10 0 0 1 2.69 2.7"
      }
    ],
    [
      "path",
      {
        "d": "M2.182 13.9a10 10 0 0 1 0-3.8"
      }
    ],
    [
      "path",
      {
        "d": "M20.279 17.609a10 10 0 0 1-2.7 2.69"
      }
    ],
    [
      "path",
      {
        "d": "M21.818 10.1a10 10 0 0 1 0 3.8"
      }
    ],
    [
      "path",
      {
        "d": "M3.721 6.391a10 10 0 0 1 2.7-2.69"
      }
    ],
    [
      "path",
      {
        "d": "M6.391 20.279a10 10 0 0 1-2.69-2.7"
      }
    ]
  ],
  "insufficient-evidence": [
    [
      "path",
      {
        "d": "M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"
      }
    ],
    [
      "path",
      {
        "d": "M12 17h.01"
      }
    ],
    [
      "path",
      {
        "d": "M9.1 9a3 3 0 0 1 5.82 1c0 2-3 3-3 3"
      }
    ]
  ],
  "ai-generated": [
    [
      "path",
      {
        "d": "M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"
      }
    ],
    [
      "path",
      {
        "d": "M20 2v4"
      }
    ],
    [
      "path",
      {
        "d": "M22 4h-4"
      }
    ],
    [
      "circle",
      {
        "cx": "4",
        "cy": "20",
        "r": "2"
      }
    ]
  ],
  "human-reviewed": [
    [
      "path",
      {
        "d": "M2 21a8 8 0 0 1 13.292-6"
      }
    ],
    [
      "circle",
      {
        "cx": "10",
        "cy": "8",
        "r": "5"
      }
    ],
    [
      "path",
      {
        "d": "m16 19 2 2 4-4"
      }
    ]
  ],
  "rule-engine": [
    [
      "path",
      {
        "d": "M12 3v18"
      }
    ],
    [
      "path",
      {
        "d": "m19 8 3 8a5 5 0 0 1-6 0zV7"
      }
    ],
    [
      "path",
      {
        "d": "M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1"
      }
    ],
    [
      "path",
      {
        "d": "m5 8 3 8a5 5 0 0 1-6 0zV7"
      }
    ],
    [
      "path",
      {
        "d": "M7 21h10"
      }
    ]
  ],
  "user-provided": [
    [
      "circle",
      {
        "cx": "12",
        "cy": "8",
        "r": "5"
      }
    ],
    [
      "path",
      {
        "d": "M20 21a8 8 0 0 0-16 0"
      }
    ]
  ],
  "external": [
    [
      "path",
      {
        "d": "M12 5v16"
      }
    ],
    [
      "path",
      {
        "d": "M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z"
      }
    ]
  ]
} as const satisfies Record<string, IconNode>;

export type PublicIconName = keyof typeof PUBLIC_ICON_NODES;

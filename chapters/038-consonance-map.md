@title The Surprising Consonance Map
@edit-time 2026-06-19T14:46Z
Draw the intervals.
Recognize the shape.
@status prelim
@pub-time 2026-03-16T00:00Z
@related 010, 034, 053, 056, 062

@argument
Draw every musical interval on a circle, score each by the simplicity of its ratio, and what appears is not a chart but The @term(Mandelbrot set, mandelbrot-set), bulb positions matching @term(Farey fractions, farey sequence), consonance ranking matching bulb size, because both are maps of stability under iteration.

@section(depth)
@image(038-consonance-map,Fourier harmonics: the overtone series underlying musical consonance,Wikimedia Commons)
Play a C and a G on a piano.
They sound stable together, resolved, at rest.
Now play a C and a G-flat.
The interval wants to move somewhere else, to resolve into something more comfortable.
Musicians have always known this, and the explanation has always been the same: simpler ratios sound more consonant.
The frequency of G is almost exactly 3/2 times the frequency of C. The frequency of G-flat is closer to 7/5, a more complex ratio, a less stable relationship.
The Pythagoreans@ref(pythagoras, "Burkert, Walter", "*Lore and Science in Ancient Pythagoreanism*. Trans. Edwin L. Minar Jr. Harvard University Press, 1972.", "Ch. V, §1 on speculation, experimentation and fiction. The ratio doctrine is genuinely Pythagorean, but Pythagoras left no writings, and the monochord and smithy stories are later legend, the smithy version physically false as told. Burkert is the standard source on what the evidence will and will not support.") noticed this in the 6th century BC, and the tradition tells it through the @term(monochord, "a single-stringed instrument used to demonstrate the relationship between string length and musical pitch. Stopping the string at 1/2 its length gives the octave, 2/3 gives the fifth, 3/4 gives the fourth.").
They didn't have a graph.
They had a single string and a remarkable idea: that number and harmony are the same thing.
Every culture that has independently developed @term(music) has found the simple ratios first.
The octave (2:1), the fifth (3:2), the fourth (4:3), these are universal.
But what does the full landscape of @term(consonance, "the perceived stability of tones sounding together, governed by the simplicity of their frequency ratio; the simpler the ratio, the more consonant the interval.") look like?
How are all the intervals related to each other, all at once?

Darakshan had wanted to see that map for a long time.
When it finally became easy enough to draw, score every ratio by how simple it is, arrange the results around a circle representing one octave, this is what appeared.
@image(harmonic-clock,The Harmonic Clock,author)

That's a Mandelbrot set.
@image(mandelbrot-boundary,The Mandelbrot Set,Wikipedia)

Not a visual resemblance.
The same object, seen from two different angles.

To understand why, you need one idea: the @term(attractor, "a value or region toward which a repeated mathematical process converges. The Mandelbrot set is a map of which starting points are attracted to stability and which escape to infinity.").
Some mathematical processes, when you repeat them, converge, they settle toward a stable value no matter where you start.
Others diverge, they spiral outward to infinity.
The boundary between the two is where things get interesting.
In the 1970s and 80s, Benoît Mandelbrot@ref(mandelbrot, "Mandelbrot, Benoit", "*The Fractal Geometry of Nature*. W.H. Freeman, 1982.", "Ch. 19, Cantor and Fatou Dusts; Self-Squared Dragons, this time for the boundary between bounded and escaping orbits and the plates that display it. The chapter carries the mathematics but not the anecdote: the expectation of a smooth boundary and the suspicion of a computer bug come from Mandelbrot's later reminiscences and are nowhere in this book.") was studying exactly this boundary for a deceptively simple formula, apply a rule, feed the result back in, repeat, and ask: does this converge or escape?
He expected the boundary to be smooth and unremarkable.
When the image came back, he thought the computer had a bug.
The boundary was infinitely complex, self-similar at every scale, inexhaustible.
He checked the program.
It was right.

What Mandelbrot had found was a map of attraction.
The large cardioid at the center is the region of simplest stability.
Around it cluster smaller bulbs, and around each of those, smaller ones still, branching without end.
Each bulb sits at a position indexed by a fraction, and the size of the bulb is governed by the simplicity of that fraction.
The bulb at position 1/2 is the largest.
The bulb at 1/3 is next.
Then 2/5, then 3/7.
The tallest bars in the harmonic chart occupy exactly those positions.
Bulb size and @term(consonance score, "a measure of how harmonious a musical interval sounds, based on the simplicity of its frequency ratio. Simpler ratios, smaller integers, score higher.") are the same ranking, expressed in two different languages.

Look again at the harmonic clock image.
Notice the wide dark gaps flanking the tallest spikes, the deep silence around the fifth and the fourth, the emptiness around the octave.
Those gaps are not accidents.
They are a provable property of the rational numbers: simple ratios repel each other.
The more consonant the interval, the wider the moat of complexity surrounding it.
This structure has a name, the Farey sequence, and the @term(mathematics) behind it belongs in the references.
What matters here is that musicians have always felt it.
The fifth sounds like itself, and nothing nearby sounds close.
The moat is arithmetic, not psychology.@ref(farey, "Farey, John", "*On a Curious Property of Vulgar Fractions*. Philosophical Magazine, 1816.", "pp. 385-386, the whole letter, which asserts the mediant property and proves nothing. The gap property this passage leans on, that neighbours a/b and c/d differ by exactly 1/bd so a simple ratio sits isolated in its own moat, was proved by Cauchy and is set out at Hardy and Wright, Ch. III, Theorems 28 to 30. Farey is the eponym, not the support.")

Mandelbrot applied a formula and found a shape he didn't expect.
Darakshan drew a map long wanted and found the same shape looking back.
Two questions, one surprise.
The echo is not coincidental, it is what happens when you draw the boundary between order and complexity, wherever you find it.

Whether that boundary also appears in the space where a neural network learns to think, where the weights that converge are separated from the weights that don't by a boundary of similar complexity, is an open question worth asking.
[056]

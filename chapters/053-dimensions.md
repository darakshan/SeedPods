@title The Virtual Dimensions Formula as a Publishable Conjecture
@status proto
@pub-time 2026-03-15T00:00Z
@related 057, 060, 038, 054, 056
@edit-time 2026-06-19T18:06Z

@argument
Replace the arbitrary tolerance in high-dimensional near-orthogonality with a principled one drawn from the @term(Farey sequence, farey-sequence), and a formula emerges, V(d,n) ~ (n²/π²)^d, that connects musical consonance, neural network superposition capacity, and quantum branching under one expression.

@section(proto)
If you have a space with d actual dimensions, how many nearly-orthogonal directions can you fit in it?
The answer matters because nearly-orthogonal directions can carry independent information without crosstalk, like independent channels.
@image(053-dimensions,High-dimensional geometry: virtual dimensions,Wikimedia Commons)

Standard mathematics (@term(Johnson-Lindenstrauss, "The result that high-dimensional data can be projected to lower dimension while approximately preserving distances; exponential in d directions.")@ref(johnson, "Johnson, William B. and Lindenstrauss, Joram", "*Extensions of Lipschitz Mappings into a Hilbert Space*. Contemporary Mathematics 26, 1984.", "Contemporary Mathematics 26, pp. 189-206, section 1, The Extension Theorems, where Lemma 1 is stated on p. 190 and proved on p. 191: for each tolerance there is a constant K such that n points embed into roughly K log n dimensions with distortion bounded by that tolerance. Inverted, the lemma says a d-dimensional space holds exponentially many nearly orthogonal directions, and the tolerance is a free parameter you simply choose, which is the arbitrariness this seedpod proposes to replace.")) already shows the answer is exponential in d. But the threshold for "nearly orthogonal" is arbitrary, you pick a tolerance ε and proceed.

The conjecture: replace the arbitrary tolerance with a principled one drawn from the Farey sequence.
The Farey sequence orders all rational numbers between 0 and 1 by complexity, simplest fractions first.
It provides a natural hierarchy of distinguishability, exactly as the ear uses it to decide which musical intervals are consonant.
The octave (1/2) and fifth (1/3) are shallow in the tree.
Dissonant intervals are deep.

The resulting formula:

**V(d, n) ~ (n²/π²)^d**

Where d is actual dimensions, n is @term(Farey depth, "The complexity level in the Farey hierarchy; used here as a principled threshold for \"nearly orthogonal,\" determining how many concepts fit at each level.") (your consonance threshold), and n²/π² is the count of Farey fractions at depth n, with π entering naturally from the circular structure of the rationals, not by assumption.

Applications: @term(neural network, neural-networks) superposition capacity, @term(Many Worlds, many-worlds) branch distinguishability, and potentially the information capacity of physical space itself.
The formula connects musical consonance, high-dimensional geometry, and quantum branching under one expression.
That connection has not been made explicitly in the literature.

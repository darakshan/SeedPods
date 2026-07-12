@title Superposition in Neural Network Representations
@status proto
@pub-time 2026-03-15T00:00Z
@related 010, 034, 035, 038, 053
@edit-time 2026-06-23T19:02Z

@argument
A @term(neural network, neural-networks) stores far more concepts than it has dimensions by packing them as nearly-orthogonal directions, more important concepts getting cleaner representations, less important ones compressed deeper, which is the same hierarchy that appears in the @term(Farey sequence, farey-sequence), in Benford's law, and in music.

@section(proto)
A neural network with d dimensions in its residual stream can represent far more than d independent concepts.
This is called @term(superposition, superposition, "storing more than d concepts in d dimensions by using nearly-orthogonal directions; studied in mechanistic interpretability.") and it has been studied carefully in the mechanistic @term(interpretability, "the research program of reverse-engineering what a trained neural network's internal representations mean; its mechanistic branch aims at circuit-level explanation.") literature@ref(elhage, "Elhage, Nelson et al.", "*Toy Models of Superposition*. Transformer Circuits Thread, Anthropic, 2022.", "The section Definitions and Motivation: Features, Directions, and Superposition, particularly the subsections Features as Directions and The Superposition Hypothesis, where the Johnson-Lindenstrauss bound gives an n-dimensional space exponentially many almost-orthogonal directions, and then the section Demonstrating Superposition, where the toy models show a trained network actually doing it.").
@image(057-superfarey,Superposition in high-dimensional neural representations,Wikimedia Commons)

The mechanism: concepts are stored as nearly-orthogonal directions in the representation space.
True orthogonality would allow exactly d independent concepts.
Near-orthogonality, with small but nonzero interference, allows exponentially more.
The network tolerates a small amount of crosstalk in exchange for vastly expanded capacity.

This is directly related to the virtual dimensions formula.
The network is implicitly choosing a @term(Farey depth), a threshold of acceptable interference, and packing in as many concepts as that threshold allows.
More important concepts get cleaner, more orthogonal representations.
Less important ones are stored in the noisier, more compressed directions deeper in the tree.

The implication: a sufficiently large neural network is not just storing information.
It is organizing information according to a natural hierarchy of importance, simpler, more fundamental concepts first, complex and specialized ones deeper.
This is the same hierarchy that appears in music, in Benford's Law, and in the Farey sequence.
The network didn't learn this hierarchy.
It fell out of the geometry.


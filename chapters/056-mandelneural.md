@title Neural Networks as High-Dimensional Mandelbrot Sets
@status proto
@pub-time 2026-03-15T00:00Z
@related 009, 011, 034, 038, 053
@edit-time 2026-06-23T19:02Z

@argument
@term(Training, training, "the iterative adjustment of a neural network's weights against a loss function, gradient descent over data; the process whose dynamics carve basins of convergence in weight space.") a @term(neural network, neural-networks) is computing a @term(Mandelbrot set, mandelbrot-set) in hundreds of thousands of dimensions, weight space is the complex plane, the loss landscape is the iteration, and the best models sit on the boundary between convergence and escape, which is not metaphor but structural homology.

@section(proto)
Training a neural network is, in a precise sense, computing a Mandelbrot set in a space of hundreds of thousands of dimensions.

The @term(weight space, weight space, "the high-dimensional space of all possible network parameters; training is iteration in this space.") is the high-dimensional analog of the complex plane.
The loss landscape is the iteration, each training step applies the rule, adjusts the weights, and checks whether the system is converging or diverging.
The trained network is a point that didn't escape, a stable attractor in weight space.

The boundary between convergence and divergence in weight space is where the interesting behavior lives.
Models near that boundary generalize well, they are poised between memorizing training data (stable interior) and failing to learn anything (escape to infinity).
The best models sit on the edge.

The bulbs of the Mandelbrot set correspond to the @term(basins of attraction, basin of attraction, "region of initial conditions that converge to the same attractor; analog of Mandelbrot bulbs."), the regions of weight space that converge to good solutions.
Larger bulbs correspond to more robust solutions, reachable from a wider range of starting points.
The branching structure of the boundary corresponds to the fine structure of @term(generalization, "a trained model's capacity to handle inputs it never saw; the fine structure of what transfers and what does not."), the increasingly subtle distinctions a deep model can make.

This is not a metaphor.
It is a structural homology between two iterative dynamical systems, one in two dimensions and one in hundreds of thousands.

@image(056-mandelneural,Julia set: neural network state space as fractal geometry,Wikimedia Commons)

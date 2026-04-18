@title Artificial Networks Rediscover the Retina
@status proto
@date 2026-03-15
@category sensation
@term AI: TBD
@term vision: TBD
@term efficient-coding: TBD
@term evolution: TBD
@related 009, 016, 037, 045, 046

@section(argument)
Deep neural networks trained on natural images with no instruction about color spontaneously develop the same opponent channels and edge detectors that evolution spent millions of years finding — because both were responding to the same mathematical pressure in the statistics of a sunlit world.

@section(proto)
When deep convolutional neural networks are trained on large collections of natural images, their first-layer filters spontaneously develop into opponent color channels and oriented edge detectors — not because anyone specified this architecture, but because it is the optimal way to encode the statistical structure of natural scenes. The network rediscovered what evolution spent millions of years finding. This convergence is predicted by the efficient coding hypothesis@ref(barlow, "Barlow, H. Redundancy reduction revisited (2001). Efficient coding and the structure of natural signals."): the visual system is structured the way it is because it is a near-optimal compression scheme for natural image statistics, and those statistics are dominated by the color temperature of sunlight, the edges of objects, and the opponent contrasts of vegetation and sky. Evolution, running on timescales of millions of years, and gradient descent, running in hours, found the same solution because they were both responding to the same underlying mathematical pressure.

@term Efficient coding hypothesis: Sensory systems are structured to optimally compress the statistics of natural inputs; predicts convergence of evolution and learning.
@image(044-ai-retina,Edge-detection filter: artificial networks rediscover retinal computation,Wikimedia Commons)

@title Artificial Networks Rediscover the Retina
@status proto
@pub-time 2026-03-15T00:00Z
@related 009, 016, 037, 045, 046
@edit-time 2026-06-19T14:46Z

@argument
Deep neural networks trained on natural images with no instruction about color spontaneously develop the same opponent channels and edge detectors that @term(evolution) spent millions of years finding, because both were responding to the same mathematical pressure in the statistics of a sunlit world.

@section(proto)
When deep convolutional neural networks are trained on large collections of natural images, their first-layer filters spontaneously develop into opponent color channels and oriented edge detectors, not because anyone specified this architecture, but because it is the optimal way to encode the statistical structure of natural scenes.
The network rediscovered what evolution spent millions of years finding.
This convergence is predicted by the @term(efficient coding hypothesis, efficient coding hypothesis, "sensory systems are structured to optimally compress the statistics of natural inputs; predicts convergence of evolution and learning.")@ref(barlow, "Barlow, Horace B.", "*Possible Principles Underlying the Transformations of Sensory Messages*. In *Sensory Communication*, ed. Walter A. Rosenblith, MIT Press, 1961, pp. 217–234.", "The original statement of the efficient coding hypothesis: sensory systems recode their input to strip redundancy given the statistics of the natural environment. Note that Barlow's later *Redundancy Reduction Revisited* (Network 12(3):241–253, 2001) partly retracts this, arguing he had over-emphasized compression and that the brain *exploits* redundancy rather than discarding it, so the 2001 paper cannot be cited for the compression claim made here.")@ref(olshausen, "Olshausen, Bruno A. and Field, David J.", "*Emergence of Simple-Cell Receptive Field Properties by Learning a Sparse Code for Natural Images*. Nature, 381:607–609, 1996.", "The result this passage actually turns on: oriented, localized, bandpass edge filters fall out of nothing but a sparse-coding objective applied to natural image patches, which is why a trained network's first layer converges on what the retina already found."): the visual system is structured the way it is because it is a near-optimal compression scheme for natural image statistics, and those statistics are dominated by the color temperature of sunlight, the edges of objects, and the opponent contrasts of vegetation and sky.
Evolution, running on timescales of millions of years, and gradient descent, running in hours, found the same solution because they were both responding to the same underlying mathematical pressure.

@image(044-ai-retina,Edge-detection filter: artificial networks rediscover retinal computation,Wikimedia Commons)

# EyeMotion: Enabling Rapid, Equitable Innovation in Ocular Biomarker Diagnostics

Neurologic diseases burden our healthcare infrastructure, while devastating patients and their families. Among these pathologies, myasthenia gravis (MG) is an urgent, costly, and underdiagnosed threat.

### Why MG?

* **Rapid Progression**: 23–30% of ocular MG (OMG) cases progress to generalized MG within two years. After such
a diagnosis, up to 20% of patients experience life-threatening *myasthenic crisis* - a respiratory failure requiring rapid medical intervention.
* **Diagnostic Pitfalls**: Early MG diagnosis is essential, but today's clinical standards lag the needs of patients. Traditional serological testing is ineffective -- up to 50% of OMG patients will result negative for AchR antibodies. The gold-standard of electrophysiology (sfEMG/RNS) is costly, slow, and unavailable in community and underserved settings.
* **Cost**: MG hospitalizations cost the U.S. $547M in 2013 - 2-4x more per patient than more well-known pathologies including Multiple Sclerosis. MG saw a staggering 13-fold rise in per-hospitalization costs between 2003 and 2013, and this number continues to climb today.
* **Inequity**: The elderly and underserved are consistently under-diagnosed, and the financial burden of hospitalization varies regionally by almost two-fold.

Today, no modern, rapid, and accurate bedside tool exists for straightforward MG diagnosis - especially for OMG, the earliest and most treatable phase of disease. *Such a gap creates missed opportunities, and causes unnecessary suffering*.

### Recent Research Can Fill This Gap

A profound opportunity for MG screening lays right before our eyes: **the eyes themselves.**

Ocular motility disturbances are among the earliest, most sensitive, and most objective biomarkers of MG - often preceding generalized weakness. Careful observation of eye movements provides a unique noninvasive window into the health of the nervous system - a potential *biomarker* to localize a broad spectrum of neurological dysfunction.

At Johns Hopkins, extensive research has validated this biomarker with promising early results:
* AI systems built on Hopkins data achieve an AUC of 0.77 for MG detection from video-oculography (VOG), with 74% balanced accuracy in initial studies.
* MG-positive and control data has been captured and analyzed in large volume, laying a foundation for future clinical trials.

But despite this proven diagnostic value, VOG tools aren't seen outside of specialized labs. The promising solutions I've mentioned are hardly available to patients -- and the reason for this is a **systems-level failure**.

* VOG headsets are **extremely costly**, and availability of headsets varies by region. A system that diagnoses patients at one hospital may be completely unusable in another.
* Software to program VOG devices is often **heavy-weight** and **difficult to understand**, making screening patients impossible in under-resourced settings.

I've seen this bottleneck play out in clinic - it's overwhelmingly clear that
our progress, however impressive, isn't making it to those who need it most. As
a future physician with an engineering background, I feel it is my
responsibility to help close this gap.

## My contribution: screening where it is needed

EyeMotion is a *critical enabler* for the next generation of oculomotor biomarker research and care.
Over the summer I've built an open infrastructure that lets every clinical/research team:

* Easily make new visual/oculomotor protocols and bring them to the bedside - with _any_ modern VR device, or even a webcam and a laptop.
* Record a uniform set of eye tracking data, and synchronize that with an annotated video - so clinicians can immediately review screening results.
* Serve patients with a system built for efficiency and privacy - so screening is possible regardless of the setting.

## Quickstart

The current hardware abstraction layer (HAL) targets the FOVE 0 headset; support for other headsets is easy to add and on the way.
For now, if you have a FOVE, install a copy of the runtime and then run this:

```bash
git clone https://github.com/jaytlang-hopkins/EyeMotion.git
cd EyeMotion
pip install -r requirements.txt
python main.py
```

That's it. Sample usage:
```
python cli.py # allows you to talk to the headset

# To launch a protocol:
[*] show okn

# To record a session:
[*] record 30s
```

### For hackers: Code Structure

|**File**	| **Role / Function**
------------|---------------------------------------------
|main.py	| Main event loop & protocol control
|cli.py	| Command-line interface
|hal.py	| Device/hardware abstraction (<i>integrates with headsets, etc</i>)
|ui.py	| Renders visual tasks (OKN, pursuit, etc)
|recorder.py	| Data capture, annotation, and export
|resources.py|	Manages paths, temp directories

### Demo

TODO!

## About the Author

I’m Jay - a post-bac premedical student at Johns Hopkins. I trained as a systems
engineer at MIT, worked at Apple, but found my calling in medicine: a field
where I can be present for everyone, regardless of the technology at hand.

It's my hope that this last-mile translational research reflects my urgency and
commitment to this field. With systems like this, we plug critical holes and
get treatments to patients quicker regardless of their circumstances. That allows providers - and future providers, like me - to do more, and be more.

## Contributing
Open an issue, pull request, or email:
* Me: jlang20@jh.edu
* Dr. Kemar Green, my mentor and PI: kgreen66@jhmi.edu

## License
GPL v3 — always open, always community-first.

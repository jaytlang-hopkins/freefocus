# FreeFocus: Enabling Rapid, Equitable Innovation in Ocular Biomarker Diagnostics

Neurological disorders are the leading cause of worldwide disease burden, accounting globally for more disability-adjusted life years (DALYs) than any other category of illness. In 2021, an estimated 3.4 billion people - 43.1% of the global population - were living with such a disease. And, across both chronic and acute neurologic dysfunction, limited diagnostic capability is consistently linked to later-stage presentations and reduced treatment efficacy - especially within rural, underserved, and minority populations.

### Recent Research Can Fill This Gap

Digital biomarkers offer a promising path forward: by enabling objective, autonomous measurement of physiologic function, they hold potential to decentralize screening, support earlier referral, and accelerate cross-site clinical trials. Among candidate biomarkers, ocular motor behavior is especially well characterized. Neural circuitry governing visual pathways broadly pervades the brain, and canonical paradigms - such as saccades, smooth pursuit, and optokinetic nystagmus - exhibit reproducible abnormalities across diverse etiologies.

Video-oculography (VOG) provides a non-invasive means to capture these signals, yielding quantitative metrics of CNS function. The proliferation of consumer-grade eye-tracking devices, from head-mounted displays (HMDs) to laptop webcams, creates an unprecedented opportunity to utilize VOG in community or telehealth contexts. However, previous VOG-based work cannot be reproduced across research centers or in resource-sparse settings due to key translational gaps:

* **Dependence on high-cost, proprietary platforms** -- Much existing literature assumes access to high-cost devices within a dedicated neuro-ocular research laboratory, or leverages dedicated compute + site-specific procedures for post-processing.
* **Lack of consideration for telemedicine** -- Previous work from Johns Hopkins utilizes an enterprise wireless network for the transmission of PII, while smartphone-based literature assumes a managed mobile device for data collection. These assumptions were not intended for outpatient or telemedical settings, where they may risk data compromise or regulatory non-compliance. 
* **Single-device, single-context silos** Most studies validate only single devices for use in identifying a single disease target. For AI-augmented diagnosis of pathology, e.g. Bachina et al., the lack of cross-device and cross-population data risks overfitting - potentially leading to false reassurance or overdiagnosis in community settings.

These barriers create a fragmented, non-interoperable evidence base for VOG-based diagnostics, stifle cross-site collaboration towards digital biomarker discovery, and hinder neurological screening efforts in non-tertiary settings.  This reflects a cross-level organizational gap in digital health infrastructure, and stands at odds with a national health strategy advocating secure, interoperable, and socioeconomically unbiased research technology.

## What could this look like?

Over the Summer of 2025, a team of neurologists and I built a proof-of-concept designed to address the above limitations. The result is a VOG platform which is easily portable and extensible - and which maintains security (data stays on-device, privilege separation is implemented) while providing niceties like real-time video annotation. Thanks to this modular design, you can use the platform on a FOVE 0 headset or...

## Demo!

...on your desktop!

The current hardware abstraction layer (HAL) will work *with your webcam*. To give this a try, run something like the following on your UNIX-like system:

```bash
git clone https://github.com/jaytlang-hopkins/FreeFocus.git
cd FreeFocus
pip install -r requirements.txt
python main.py --device screen
```

That's it. Sample usage:
```
# To launch a protocol:
[*] show okn

# To record your eyes:
[*] record 30s

# To see all FreeFocus has to offer:
[*] help
```

Granted, eye tracking with only a webcam isn't _ideal_ -- but this is supposed to prove that these sorts of technologies can work.

## Architecture Overview

FreeFocus is built around a modular, event-driven architecture for maintainability and extensibility:

| **File/Folder**         | **Role / Function**                                              |
|------------------------|------------------------------------------------------------------|
| `main.py`              | Clinician interaction, bootstraps the FreeFocus daemon |
| `ipc/`                 | Inter-process communication (IPC) logic, command parsing, privilege separation |
| `hal/`                 | Device/hardware abstraction (integrates with headsets, etc)       |
| `ui.py`                | Renders visual tasks (OKN, pursuit, etc)                         |
| `recorder.py`          | Data capture, annotation, and export                              |
| `resources.py`         | Manages paths, temp directories                                   |

**Key features:**
- Modular IPC system with privilege-separated engine process
- Event-driven ECS (Entity Component System) using `esper`
- Extensible command system (add new stimuli easily)
- Device-agnostic hardware abstraction
- Text-based, interactive CLI for scriptable, approachable testing

## About the Author

I’m Jay - a post-bac premedical student at Johns Hopkins. I trained as a
systems engineer at MIT, worked at Apple, but found my calling in medicine: a
field where I can be present for everyone, regardless of the technology at
hand.

With systems like this one, informed from clinical context, we plug critical
holes and get treatments to patients quicker regardless of their circumstances.
That allows providers - and future providers, like me - to do more, and be
more.

## Contributing
Open an issue, pull request, or [email me](mailto:jlang20@jh.edu)

## License
GPLv3 — always open, always community-first.

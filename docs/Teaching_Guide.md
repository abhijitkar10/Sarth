# Knee MRI Project: A Simple-Words Teaching Guide

*For the mid-semester evaluation. Read it once from top to bottom. Then use Part 6 (the slide-by-slide script) when you practise.*

**Contents**

1. The project in one minute
2. The ideas you need, in plain words
3. How the pipeline works (follow Figure 1)
4. What we used and what we added
5. The experiments and results, in plain words
6. Slide-by-slide speaking script
7. Questions you may be asked, with simple answers
8. Numbers cheat sheet
9. Glossary
10. Using the slides in Google Slides

---

## 1. The project in one minute

**The problem.** A knee MRI is a stack of grey pictures. A radiologist studies them and writes down what is wrong: a torn ligament, worn cartilage, extra fluid in the joint, and so on. The RSNA 2026 challenge on Kaggle asks one question: can a computer look at the MRI and give a score for 12 possible problems?

**What we did.** We did not train one new giant model. We took three strong models that other people had already trained, each built in a different way, and showed them the same MRI. Then we combined their opinions into one score per problem. On top of that we added a small extra layer called **ABG**, to see whether it could squeeze out a little more accuracy.

**What happened.** Our parent pipeline (without ABG) scored **0.940** on the public leaderboard. With ABG it scored **0.922**. So ABG did not help.

**What we learned.** In our practice world (a simulation) small add-ons change the score by thousandths, not by 0.018. So the drop is larger than the design of ABG alone should cause, and we say plainly that the cause is not isolated.

Three sentences to remember:

1. "We combined three pretrained model families by rank blending."
2. "Our own work is the ABG layer, the experiment design and checks, and the simulation study."
3. "ABG did not beat its parent, and we can explain what that does and does not tell us."

---

## 2. The ideas you need, in plain words

**MRI, series and slices.** An MRI scanner takes many thin pictures, called *slices*, through the knee. One set of slices taken with one setting is a *series*. One exam has several series: seen from the side (*sagittal*), from the front (*coronal*) and from above (*axial*). Some are *fat-suppressed* (fat is made dark, so fluid and swelling stand out) and some are *structural* (they show the anatomy clearly).

**The 12 findings.** Two ligaments (ACL, MCL). Two meniscus pads (medial, lateral). Wear of the joint, called osteoarthritis or OA (medial, lateral, patellofemoral). Extra fluid (effusion), an inflamed lining (synovitis) and a fluid pocket behind the knee (Baker's cyst). A bone bruise (contusion) and a break (fracture).

**AUC, the score.** Pick one knee that has the problem and one that does not, at random. AUC is the chance that the model gives the higher score to the knee with the problem. 0.5 is a coin flip. 1.0 is perfect. The leaderboard score is the average of the 12 AUCs (the *macro AUC*). So 0.94 means: on average, a knee with a problem is ranked above a healthy knee 94 times out of 100. Only the order of the scores matters, not their exact size.

**Ensemble.** Ask several different experts and combine their answers. If they make different mistakes, the mistakes partly cancel.

**Pretrained model.** A model that already learned from a huge number of images before we touched it. It is like hiring someone with years of experience instead of training a beginner. We use such models as they were released.

**Transformer (DINO).** It cuts the picture into small squares called patches. Then every patch "looks at" every other patch to decide which ones matter. That looking is called *attention*. DINO is a version made by Meta that learned from many pictures without needing labels. We use DINOv2-small for 20 of our models and DINOv3 ViT-S for 5 more.

**CNN (RadImageNet).** A CNN slides small windows over the picture to find edges, then textures, then shapes. RadImageNet is a CNN (a ResNet-50) that learned from medical pictures instead of everyday photos.

**CoAtNet.** A mix of the two ideas: the CNN part sees local detail and the attention part sees the big picture.

**Slot head.** Our input has six views, like six folders. For each of the 12 findings the head learns which folders to read most. A missing folder is simply ignored.

**Rank blending.** Different models give scores on different scales, for example one from 0 to 1 and another from 0 to 100. To combine them fairly we replace each score by its rank position, like a class rank, and then average the ranks. AUC only cares about order, so nothing important is lost.

**Calibration.** Adjusting a model's raw outputs onto a sensible scale. The calibrator in our pipeline is *frozen*: we did not change it.

**Residual.** A small correction. If two similar models disagree a little, the difference is a hint, so we add a small multiple of it.

**Gain averaging (test-time augmentation).** Look at the same scan at slightly different brightness (times 0.9, 1.0 and 1.1) and average the answers, so one odd brightness cannot mislead the model. We give the middle view the most weight (1/6, 4/6, 1/6).

**Ablation.** Switch one part on or off and see what happens to the score. It tells you what each part is worth.

**Simulation.** A practice world made of fake data where we control the rules. It cannot tell us how good our models are on real knees. It shows how the ideas behave, for example why more models help less and less.

**Public leaderboard and hidden test set.** Kaggle keeps the true answers secret. We submit the notebook, Kaggle runs it on hidden exams, and shows the score. The *public* score uses part of that hidden data.

---

## 3. How the pipeline works (follow Figure 1)

Open slide 7 (the full figure) and walk from left to right.

1. **Input.** One exam is several series of slices.
2. **Preprocessing.** The program reads the DICOM headers (the labels inside the files) to find the plane, the side and whether fat was suppressed. It puts each series into one of six slots (three planes times two types). Right knees are flipped so every knee faces the same way. The knee is cropped to about 130 mm, resized, and 12 to 16 slices are chosen. A missing slot is masked, never invented.
3. **Three branches look at the same slots.**
   - *DINO transformers:* 25 small ViT models (20 from DINOv2-small, 5 "A5" folds from DINOv3). A slot head lets each finding choose its best views.
   - *RadImageNet ResNet-50:* features go to several head families, then to the frozen calibrator.
   - *CoAtNet:* the Raptor model with 4 arms (mixed 60, 10, 10, 20 percent) plus a residual CoAtNet.
4. **Fusion by rank.** The A5 folds join the DINO blend with weight 0.45. The DINO/Rad side (call it T) and the CoAtNet side (call it H) are blended: final = 40 percent T plus 60 percent H. For the lateral meniscus the final score is H alone.
5. **Outputs.** Twelve scores, plus a receipt: a fingerprint (SHA-256) of the settings and the final file, so every submission can be checked later.

**Careful with stage 4 in the figure.** The figure draws layers of connected nodes there. That is a schematic. In our pipeline there are no extra trained layers: the twelve scores come from rank blending. The slide says this too.

---

## 4. What we used and what we added

| Part | Where it comes from | Our role |
|---|---|---|
| 20 DINO ensemble members | pilkwang's public release (DINOv2-small backbone from Meta) | used as released |
| 5 A5 folds | Mattia Angeli's public release (DINOv3 ViT-S/16) | used as released |
| RadImageNet ResNet-50 and heads | RadImageNet; heads by Antoine and Sofia Anjenje; weights mirror by Marwan | used as released |
| Raptor CoAtNet | Johnathan Wagner (DreadDevelopment) | used as released |
| Residual CoAtNet | Mattia Angeli | used as released |
| Parent pipeline (V17 recipe) | reproduces Angeli's V27 prediction graph; our first submission, scored 0.940 | ran and verified it |
| ABG layer (A, B, G) | us | designed it and ran it |
| Experiment protocol | us | fixed before any score was seen |
| Checks and hashed receipt | us | added to every submission |
| Dropped-idea evaluations | us | tested against gates set in advance |
| Simulation study | us | wrote and ran it |

**How to say it.** "We built on public pretrained models and made three contributions: the ABG layer, an experiment protocol with checks, and a simulation study."

That is a fair and respectable project. Combining and testing strong models is how most Kaggle teams work. What matters is that you say clearly which part is yours. Do not say that you trained the base models from scratch: the references slide and the Kaggle notebook both say they are public releases, and a question about it has a simple true answer.

---

## 5. The experiments and results, in plain words

### 5.1 What ABG adds

- **A (native E11 residual).** Five extra heads give a second opinion. We take their difference from another head (E13) and add 0.15 of it after calibration.
- **B (alternate Rad residual).** Another family of RadImageNet heads gives a small correction, scaled by about 0.425, with no extra pass through the encoder.
- **G (gain averaging).** Each CoAtNet arm is averaged over three brightness gains (0.9, 1.0, 1.1) with weights 1/6, 4/6, 1/6.

None of these trains anything new. The scales were inherited, not fitted to the leaderboard, and the plan was fixed before any score was seen.

### 5.2 Ablation I: ensembles help, then flatten (simulation)

Slide 14 shows two charts made on fake data (1,500 exams times 12 findings, 40 repeats).

- *Left chart.* One model scores 0.899. Two models give 0.917. Twenty give 0.934. Going from 10 to 20 models adds only +0.002. Reading: the first few models help a lot, later ones barely help.
- *Right chart.* Blending three model families beats the DINO ensemble alone by +0.028 when their mistakes are very different (correlation 0.2). When the families make the same mistakes (correlation 0.8) the blend is −0.003 compared with DINO alone. Reading: blending only pays when the models see the problem differently.

### 5.3 Ablation II: switching A, B and G on and off (simulation)

Slide 15 uses a toy copy of our pipeline on fake data. Each bar is the change in macro AUC compared with the parent.

| Configuration | Added heads as good as the ones they replace | If the added heads are 0.03 AUC worse | If the added heads are 0.02 AUC better |
|---|---|---|---|
| A | −0.0001 | −0.0009 | +0.0005 |
| B | −0.0006 | −0.0032 | +0.0010 |
| G | −0.0001 | −0.0001 | −0.0001 |
| A and B | −0.0007 | −0.0042 | +0.0015 |
| A, B and G (ABG) | −0.0008 | −0.0043 | +0.0014 |

How to read it: every combination moves the score by thousandths. Whether the change is good or bad depends on whether the added heads are better or worse than the ones they are compared with. B has the biggest effect because its scale (0.425) is bigger than A's (0.15). G changes almost nothing here.

**Stress test.** To lose as much as the real result (0.018), the toy model needs added heads about 0.15 AUC worse, which gives −0.019. That is a very bad head, far worse than ordinary design noise.

**Important.** All of this is fake data with assumed settings. It shows how the ideas behave. It is not a measurement of our real models, and the slides say so on every simulation slide.

### 5.4 Ideas we tried and dropped (real, from our recorded evaluations)

- **OrthoDiffusion on ACL:** small positive gain (+0.00226), but the confidence check scored 0.677 where 0.80 was needed. On MCL and the menisci it was negative. Dropped.
- **Anchor-bilinear residual:** ACL gain of about +0.00095, which is only about +0.00008 on the macro score. Below the floor we set. Dropped.
- **LCSE anatomical residual:** ACL change of about −0.00109, and all six gates failed. We made no submission.

The lesson: we set the pass marks before looking, and a failed mark stays failed, even if a later score looks nice.

### 5.5 The two scores, and what we can honestly say

- Parent (V17 recipe): **0.940**. ABG: **0.922**. Difference: **−0.018**.
- A, B and G were graded together, so we cannot say which of them, if any, caused the drop.
- The simulation says design noise alone should cost thousandths, so the real drop needs a closer look.
- Possible reasons, all unproven: the added heads may simply be weaker on the test data; they may have been trained in a slightly different way from how they are used at test time; the three changes may interact.

What you can say with confidence: "ABG did not help on the public leaderboard." What you should not say: any claim about which part caused it.

---

## 6. Slide-by-slide speaking script

About 30 to 60 seconds per slide. For a 12-minute talk, skip the appendix and speed through slides 2, 5 and 13.

**Slide 1: Title.** "Our project is an auditable ensemble of three pretrained model families for the RSNA 2026 knee MRI challenge. Auditable means every run is checked and leaves a receipt."

**Slide 2: Outline.** "We will cover the problem, the method, our experiments, the results, and what we learned."

**Slide 3: Abstract.** "Knee MRI reading varies between doctors. The challenge asks for scores for 12 problems, judged by mean AUC. We combined three model families by rank blending and added a small experiment layer called ABG. Our parent scored 0.940 and ABG 0.922, and a simulation helps us think about why."

**Slide 4: Why knee MRI.** "MRI shows the whole joint. Readers disagree and specialists are scarce. This is RSNA's first musculoskeletal challenge with images and multilingual reports: over 5,000 training exams, 12 languages, 16 sites."

**Slide 5: The task.** "There are 12 findings in five groups. The score is the mean AUC of the 12. Kaggle limits us to two T4 GPUs, no internet and eight hours."

**Slide 6: Approach.** "On the left is what we built on: three public pretrained families, credited in the references. On the right is our own work: the ABG layer, experiments fixed in advance, and checked, hashed runs."

**Slide 7: Pipeline overview.** "This is our pipeline. Input on the left, preprocessing, three branches in the middle, fusion, and twelve scores on the right. The next slides zoom in. Note that stage 4 is only a schematic: we blend ranks and train no new network."

**Slide 8: Input and preprocessing.** "We read the DICOM headers, put each series into one of six slots, flip right knees, crop about 130 millimetres and choose 12 to 16 slices. A missing slot is masked, never invented."

**Slide 9: DINO branch.** "Slices become patches and attention finds the important regions. There are 25 small ViT models: 20 from DINOv2 and 5 from DINOv3. A slot head lets each finding choose its best views. The DINOv3 folds enter the blend at weight 0.45."

**Slide 10: RadImageNet and CoAtNet.** "RadImageNet is a CNN trained on medical images. CoAtNet mixes convolution and attention over four views. The orange box marks the brightness averaging, our G addition."

**Slide 11: Rank fusion.** "We blend by rank so no model's scale dominates. Box 1 is the 0.45 weight. Box 2 shows CoAtNet carrying 60 percent of each score and 100 percent for the lateral meniscus."

**Slide 12: ABG.** "A and B add small corrections after calibration. G averages three brightness views. No new training, scales inherited, and everything fixed before we saw a score."

**Slide 13: Setup and checks.** "Each run is a full Kaggle notebook on a hidden test set. We checked the GPUs, the weights, every stage's shapes and IDs, the arms, the exact gain reconstruction, and we hashed the final file. These checks prove the run was correct, not that the AUC is good."

**Slide 14: Ablation I.** "This is a simulation on fake data. More models help, then flatten: from 10 to 20 models we gain only 0.002. Blending families helps most when their errors differ."

**Slide 15: Ablation II.** "Again simulation. We switch A, B and G on and off. Everything moves the score by thousandths, and the sign depends on whether the added heads are better or worse. The real ABG result, minus 0.018, is far outside this range, so design noise alone does not explain it."

**Slide 16: Dropped ideas.** "We tested three more ideas against pass marks set in advance. All failed, and we did not submit them. A failed gate stays failed."

**Slide 17: Results.** "Parent 0.940, ABG 0.922, a difference of minus 0.018. The grey bars are public reference points from mid-August, so they are old."

**Slide 18: What we learned.** "ABG did not help, and because A, B and G were graded together we cannot say which one is responsible. Our limits: nothing new was trained, there is no held-out validation, the scores are rank scores, and per-addition effects were studied in simulation."

**Slide 19: Conclusion and future work.** "The ensemble runs reproducibly inside Kaggle's limits. The extra layer did not help, which is a useful negative result. Next we would isolate A, B and G on a labelled held-out set and check the added heads for a train-test mismatch."

**Slide 20: References.** "All the public releases are credited here, with their licences."

**Slide 21: Thank you.** "Thank you. Questions are welcome."

**Slides 22 to 24: Appendix.** Use only if asked: the exact ABG formulas, the input sizes per model, and two extra simulation charts.

---

## 7. Questions you may be asked, with simple answers

**Did you train these models yourselves?** No. The base models are public pretrained releases, credited on our references slide. Our own work is the ABG layer, the experiment design and checks, the dropped-idea evaluations and the simulation study.

**Why combine several models?** Different models make different mistakes. Averaging their ranks cancels part of the mistakes. The ablation shows this works best when the models are really different.

**What is AUC, and why the mean of 12?** AUC is the chance that a knee with the problem gets a higher score than a healthy knee. The challenge scores each finding separately and averages the 12, so every finding counts equally.

**Why rank blending and not just averaging the scores?** The models use different scales. Ranks put them on one scale. AUC only depends on order, so ranks lose nothing that matters.

**Why did ABG score lower than the parent?** We do not know yet. A, B and G were graded together. Our simulation says design noise alone should cost thousandths, so the drop suggests the added heads behave much worse than assumed on the test data. We would test each part separately on a labelled held-out set.

**Is the simulation real data?** No. It uses fake data with assumed settings and is labelled on every slide. It shows how the ideas behave. It does not measure our real models.

**Why do you not have real ablation numbers for A, B and G?** They were graded only as a combined submission. We therefore studied each part in simulation and we say clearly that this is simulation, not a leaderboard result.

**Can this be used on patients?** No. The output is a research ranking score, not a calibrated probability, and a leaderboard score does not prove performance on other scanners or patients.

**What is stage 4 (MLP heads) in the figure?** It is a schematic. In our pipeline the final combination is rank blending and no new network was trained.

**What does a frozen calibrator mean?** It is a small, already-fitted step that adjusts one branch's outputs. We left it untouched, and added A and B after it.

**Why six slots?** Three planes (side, front, top) times two sequence types (fat-suppressed and structural). That fixed layout lets every model see the same kind of view in the same place. Missing views are masked.

**What is the difference between DINOv2 and DINOv3?** Both are self-supervised vision transformers from Meta. DINOv3 is the newer one. Our 20 ensemble members use DINOv2-small backbones and the 5 A5 folds use DINOv3 ViT-S/16.

**What does gain averaging do?** It looks at each scan at three brightness levels and averages, so the answer depends less on scanner brightness.

**How do you know the run was correct?** We checked the GPUs, matched the weights of all 20 DINO members, checked shapes, IDs and ranges at every stage, confirmed the exact gain reconstruction, and hashed the final file. These checks prove the run is correct. They do not measure AUC.

**What is the public leaderboard and can it mislead?** It is the score on part of the hidden test data. It can differ from the final private score, so it should not be over-read.

**What would you do next?** Test A, B and G one at a time on a labelled held-out set with patient-level splits, check the added heads for a train-test mismatch, and calibrate the simulation to real behaviour.

**What are the licences?** Our notebook code is Apache 2.0, several datasets are CC0, the RadImageNet-based heads are CC-BY-NC-SA 4.0 (non-commercial), and DINOv3 has its own Meta licence.

---

## 8. Numbers cheat sheet

| Number | Meaning | Real or simulated |
|---|---|---|
| 5,000+ exams, 12 languages, 16 sites | the challenge's training data | real (RSNA announcement) |
| 12 | findings scored | real |
| 2 x T4, internet off, 8 hours | Kaggle limits | real |
| 25 (20 + 5) | ViT-S models in the DINO branch | real |
| 0.45 | weight of the A5 folds in the DINO blend | real |
| 60% (100% lateral meniscus) | share of the CoAtNet side in the final score | real |
| 60 / 10 / 10 / 20 | mix of the four Raptor arms (percent) | real |
| 0.9 / 1.0 / 1.1 with 1/6, 4/6, 1/6 | brightness gains and their weights | real |
| 0.15 and 0.425 | scales of the A and B residuals | real |
| 0.940 | parent score, public leaderboard | real |
| 0.922 | ABG score, public leaderboard | real |
| −0.018 | ABG minus parent | real |
| 0.677 against 0.80 | OrthoDiffusion confidence against the bar | real (recorded evaluation) |
| +0.00226, +0.00095, −0.00109 | ACL changes of the three dropped ideas | real (recorded evaluation) |
| 0.932 to 0.934 | ensemble of 10 to 20 members | simulated |
| +0.028 and −0.003 | blend against DINO alone at correlation 0.2 and 0.8 | simulated |
| −0.0008 | ABG, heads as good as the ones they replace | simulated |
| −0.0043 | ABG, heads 0.03 AUC worse | simulated |
| −0.019 | ABG, heads about 0.15 AUC worse (stress test) | simulated |
| about 0.92 and about 0.951 | shared public notebooks and top public score in mid-August | real but old (Kaggle forum) |

---

## 9. Glossary

| Word | Simple meaning |
|---|---|
| ACL, MCL | two ligaments that hold the knee together |
| Meniscus | a cartilage pad that cushions the knee |
| OA | osteoarthritis, wear of the joint |
| Effusion | extra fluid in the joint |
| Synovitis | inflamed joint lining |
| Baker's cyst | a fluid pocket behind the knee |
| DICOM | the file format of medical scans, with labels inside |
| Sagittal, coronal, axial | the knee seen from the side, front and top |
| Fat-suppressed | a scan setting that makes fluid stand out |
| Slot | one of six fixed places for a view in our input |
| Ensemble | several models whose answers are combined |
| ViT | vision transformer, a model that uses attention on picture patches |
| DINO | Meta's self-supervised ViT |
| CNN | a network that slides small windows over a picture |
| ResNet-50 | a well-known CNN |
| RadImageNet | a CNN trained on medical images |
| CoAtNet | a CNN and attention hybrid |
| Raptor | the CoAtNet model we used, made by another Kaggle author |
| Slot head | the part that lets each finding pick its best views |
| Rank blending | averaging rank positions instead of raw scores |
| Calibrator | a fitted step that puts outputs on a sensible scale |
| Residual | a small correction added to a score |
| TTA, gain averaging | averaging answers over slightly different inputs |
| AUC | chance that a sick case scores above a healthy one |
| Macro AUC | the average of the 12 AUCs |
| Ablation | switching a part on or off to see its effect |
| Simulation | a practice world of fake data |
| Public leaderboard | Kaggle's score on part of the hidden test data |
| SHA-256 | a fingerprint of a file, used in our receipt |

---

## 10. Using the slides in Google Slides

1. Open Google Slides, then choose **File, Import slides**, and upload `RSNA_Knee_MRI_MidSem_Deck.pptx`.
2. Select all slides and import them.
3. The deck uses only Calibri and Cambria, which Google Slides has, so the layout should stay the same.
4. The charts are pictures on purpose, because Google Slides cannot edit PowerPoint charts. The numbers come from `simulation/results.json`.
5. The speaker notes come across. Open them with **View, Show speaker notes**.
6. Add your team and guide names on slide 1.

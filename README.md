## Controllable Safety Alignment
This is the codebase for our ICLR 2025 paper [*Controllable Safety Alignment: Inference-Time Adaptation to Diverse Safety Requirements*](https://arxiv.org/abs/2410.08968).

Please see a summary of our artifacts in our HuggingFace collection: [Controllable Safety Alignment 🤗](https://huggingface.co/collections/microsoft/controllable-safety-alignment-68019c03f7864df1b4b7a1b7).

In addition to the codebase, we have publicly released the CoSApien dataset. Soon, we will release the CoSAlign model and synthetic datasets. 

- **CoSApien👥 dataset**: [link](https://huggingface.co/datasets/microsoft/CoSApien)

If you have questions feel free to email the authors.

## Evaluating Controllability

Please use `run_eval_multistep.sh` to evaluate controllability. This script pipelines the steps needed for evaluation: 

- (1) The candidate model generate response on the test set
- (2) Generate evaluation response from the evaluator model
- (3) Parse evaluation responses and aggregate final evaluation results

You will need to provide the name (or path) of the candidate model, a pretty name of the candidate model, and the name of the system prompt template as *command line arguments*.

## Constructing the CoSAlign Training Data

We detail the process for CoSAlign data creation in the `data_processing/` directory. Please see `data_processing/README.md` for details.

## Conducting SFT and DPO

We use the code adapted from the [DPO repo](https://github.com/eric-mitchell/direct-preference-optimization/) for conducting SFT and DPO. Please see more details in the `dpo/` directory. Please see our provided example training script in `dpo/train.sh`.

## Reference
If you find our work useful, please consider citing our paper:
```bibtex
@inproceedings{zhang2025controllablesafetyalignment,
      title={Controllable Safety Alignment: Inference-Time Adaptation to Diverse Safety Requirements}, 
      author={Jingyu Zhang and Ahmed Elgohary and Ahmed Magooda and Daniel Khashabi and Benjamin Van Durme},
      year={2025},
      url={https://arxiv.org/abs/2410.08968},
      booktitle = {International Conference on Learning Representations (ICLR)}
}
```

import warnings

import torch.nn as nn

from ....models.distilbert.modeling_distilbert import (
    DISTILBERT_INPUTS_DOCSTRING,
    DISTILBERT_START_DOCSTRING,
    DistilBertModel,
    DistilBertPreTrainedModel,
)
from ....utils import add_start_docstrings, add_start_docstrings_to_model_forward
from ...heads import (
    BertStyleMaskedLMHead,
    BiaffineParsingHead,
    CausalLMHead,
    ClassificationHead,
    ModelWithFlexibleHeadsAdaptersMixin,
    MultiLabelClassificationHead,
    MultipleChoiceHead,
    QuestionAnsweringHead,
    TaggingHead,
)


@add_start_docstrings(
    """DistilBert Model transformer with the option to add multiple flexible heads on top.""",
    DISTILBERT_START_DOCSTRING,
)
class DistilBertAdapterModel(ModelWithFlexibleHeadsAdaptersMixin, DistilBertPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.distilbert = DistilBertModel(config)

        self._init_head_modules()

        self.init_weights()

    def get_position_embeddings(self) -> nn.Embedding:
        """
        Returns the position embeddings
        """
        return self.distilbert.get_position_embeddings()

    def resize_position_embeddings(self, new_num_position_embeddings: int):
        """
        Resizes position embeddings of the model if :obj:`new_num_position_embeddings !=
        config.max_position_embeddings`.

        Arguments:
            new_num_position_embeddings (:obj:`int`):
                The number of new position embedding matrix. If position embeddings are learned, increasing the size
                will add newly initialized vectors at the end, whereas reducing the size will remove vectors from the
                end. If position embeddings are not learned (*e.g.* sinusoidal position embeddings), increasing the
                size will add correct vectors at the end following the position encoding algorithm, whereas reducing
                the size will remove vectors from the end.
        """
        self.distilbert.resize_position_embeddings(new_num_position_embeddings)

    @add_start_docstrings_to_model_forward(DISTILBERT_INPUTS_DOCSTRING.format("batch_size, num_choices"))
    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        head_mask=None,
        inputs_embeds=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,
        head=None,
        **kwargs
    ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        input_ids = input_ids.view(-1, input_ids.size(-1)) if input_ids is not None else None
        attention_mask = attention_mask.view(-1, attention_mask.size(-1)) if attention_mask is not None else None
        inputs_embeds = (
            inputs_embeds.view(-1, inputs_embeds.size(-2), inputs_embeds.size(-1))
            if inputs_embeds is not None
            else None
        )

        distilbert_output = self.distilbert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        outputs = self.forward_head(
            distilbert_output, head_name=head, attention_mask=attention_mask, return_dict=return_dict, **kwargs
        )

        return outputs

    head_types = {
        "classification": ClassificationHead,
        "multilabel_classification": MultiLabelClassificationHead,
        "tagging": TaggingHead,
        "multiple_choice": MultipleChoiceHead,
        "question_answering": QuestionAnsweringHead,
        "dependency_parsing": BiaffineParsingHead,
        "masked_lm": BertStyleMaskedLMHead,
        "causal_lm": CausalLMHead,
    }

    def add_classification_head(
        self,
        head_name,
        num_labels=2,
        layers=2,
        activation_function="tanh",
        overwrite_ok=False,
        multilabel=False,
        id2label=None,
        use_pooler=False,
    ):
        """
        Adds a sequence classification head on top of the model.

        Args:
            head_name (str): The name of the head.
            num_labels (int, optional): Number of classification labels. Defaults to 2.
            layers (int, optional): Number of layers. Defaults to 2.
            activation_function (str, optional): Activation function. Defaults to 'tanh'.
            overwrite_ok (bool, optional): Force overwrite if a head with the same name exists. Defaults to False.
            multilabel (bool, optional): Enable multilabel classification setup. Defaults to False.
        """

        if multilabel:
            head = MultiLabelClassificationHead(
                self, head_name, num_labels, layers, activation_function, id2label, use_pooler
            )
        else:
            head = ClassificationHead(self, head_name, num_labels, layers, activation_function, id2label, use_pooler)
        self.add_prediction_head(head, overwrite_ok)

    def add_multiple_choice_head(
        self,
        head_name,
        num_choices=2,
        layers=2,
        activation_function="tanh",
        overwrite_ok=False,
        id2label=None,
        use_pooler=False,
    ):
        """
        Adds a multiple choice head on top of the model.

        Args:
            head_name (str): The name of the head.
            num_choices (int, optional): Number of choices. Defaults to 2.
            layers (int, optional): Number of layers. Defaults to 2.
            activation_function (str, optional): Activation function. Defaults to 'tanh'.
            overwrite_ok (bool, optional): Force overwrite if a head with the same name exists. Defaults to False.
        """
        head = MultipleChoiceHead(self, head_name, num_choices, layers, activation_function, id2label, use_pooler)
        self.add_prediction_head(head, overwrite_ok)

    def add_tagging_head(
        self, head_name, num_labels=2, layers=1, activation_function="tanh", overwrite_ok=False, id2label=None
    ):
        """
        Adds a token classification head on top of the model.

        Args:
            head_name (str): The name of the head.
            num_labels (int, optional): Number of classification labels. Defaults to 2.
            layers (int, optional): Number of layers. Defaults to 1.
            activation_function (str, optional): Activation function. Defaults to 'tanh'.
            overwrite_ok (bool, optional): Force overwrite if a head with the same name exists. Defaults to False.
        """
        head = TaggingHead(self, head_name, num_labels, layers, activation_function, id2label)
        self.add_prediction_head(head, overwrite_ok)

    def add_qa_head(
        self, head_name, num_labels=2, layers=1, activation_function="tanh", overwrite_ok=False, id2label=None
    ):
        head = QuestionAnsweringHead(self, head_name, num_labels, layers, activation_function, id2label)
        self.add_prediction_head(head, overwrite_ok)

    def add_dependency_parsing_head(self, head_name, num_labels=2, overwrite_ok=False, id2label=None):
        """
        Adds a biaffine dependency parsing head on top of the model. The parsing head uses the architecture described
        in "Is Supervised Syntactic Parsing Beneficial for Language Understanding? An Empirical Investigation" (Glavaš
        & Vulić, 2021) (https://arxiv.org/pdf/2008.06788.pdf).

        Args:
            head_name (str): The name of the head.
            num_labels (int, optional): Number of labels. Defaults to 2.
            overwrite_ok (bool, optional): Force overwrite if a head with the same name exists. Defaults to False.
            id2label (dict, optional): Mapping from label ids to labels. Defaults to None.
        """
        head = BiaffineParsingHead(self, head_name, num_labels, id2label)
        self.add_prediction_head(head, overwrite_ok)

    def add_masked_lm_head(self, head_name, activation_function="gelu", overwrite_ok=False):
        """
        Adds a masked language modeling head on top of the model.

        Args:
            head_name (str): The name of the head.
            activation_function (str, optional): Activation function. Defaults to 'gelu'.
            overwrite_ok (bool, optional): Force overwrite if a head with the same name exists. Defaults to False.
        """
        head = BertStyleMaskedLMHead(self, head_name, activation_function=activation_function)
        self.add_prediction_head(head, overwrite_ok=overwrite_ok)

    def add_causal_lm_head(self, head_name, activation_function="gelu", overwrite_ok=False):
        """
        Adds a causal language modeling head on top of the model.

        Args:
            head_name (str): The name of the head.
            activation_function (str, optional): Activation function. Defaults to 'gelu'.
            overwrite_ok (bool, optional): Force overwrite if a head with the same name exists. Defaults to False.
        """
        head = CausalLMHead(
            self, head_name, layers=2, activation_function=activation_function, layer_norm=True, bias=True
        )
        self.add_prediction_head(head, overwrite_ok=overwrite_ok)


class DistilBertModelWithHeads(DistilBertAdapterModel):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "This class has been renamed to `{}` in v3. "
            "Please use the new class instead as this class might be removed in a future version.".format(
                self.__class__.__bases__[0].__name__
            ),
            FutureWarning,
        )
        super().__init__(*args, **kwargs)

    @classmethod
    def from_config(cls, config):
        warnings.warn(
            "This class has been renamed to `{}` in v3. "
            "Please use the new class instead as this class might be removed in a future version.".format(
                cls.__bases__[0].__name__
            ),
            FutureWarning,
        )
        return super().from_config(config)

    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path, *model_args, **kwargs):
        warnings.warn(
            "This class has been renamed to `{}` in v3. "
            "Please use the new class instead as this class might be removed in a future version.".format(
                cls.__bases__[0].__name__
            ),
            FutureWarning,
        )
        return super().from_pretrained(pretrained_model_name_or_path, *model_args, **kwargs)
